import re

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.base import logger
from django.db.utils import DatabaseError
from django.db.utils import Error
from django.db.utils import NotSupportedError
from django.db.utils import OperationalError

try:
    import ydb_dbapi as Database  # noqa: N812
except ImportError:
    Database = None

if Database is None:
    raise ImproperlyConfigured(
        "Error loading ydb_dbapi module. Install it using 'pip install ydb_dbapi'."
    )

# ydb_dbapi does not expose the DB-API 2.0 ``Binary`` type constructor that
# Django calls as ``connection.Database.Binary(value)`` in
# BinaryField.get_db_prep_value(). Binary values map to YDB's String type,
# whose driver representation is Python ``bytes``, so ``bytes`` is the correct
# constructor. Guarded so a future ydb_dbapi that ships ``Binary`` wins.
if not hasattr(Database, "Binary"):
    Database.Binary = bytes

from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor
from .validation import DatabaseValidation


def _normalize_isolation_level(value):
    """
    Map a ``DATABASES["OPTIONS"]["isolation_level"]`` setting to a ydb_dbapi
    ``IsolationLevel``.

    The level is given as a case-insensitive string (e.g. ``"serializable"`` or
    ``"snapshot readonly"``); underscores are treated as spaces so the enum
    member spelling works too. Raise ``ImproperlyConfigured`` for an unknown
    level so misconfiguration fails fast at connect time.
    """
    levels = Database.IsolationLevel
    if isinstance(value, levels):
        return value
    normalized = " ".join(str(value).upper().replace("_", " ").split())
    try:
        return levels(normalized)
    except ValueError:
        allowed = ", ".join(sorted(level.value.lower() for level in levels))
        msg = (
            f"Unknown isolation_level {value!r} in DATABASES OPTIONS for the "
            f"YDB backend. Supported values: {allowed}."
        )
        raise ImproperlyConfigured(msg) from None


class DatabaseWrapper(BaseDatabaseWrapper):
    """
    Represent a database connection.
    """

    vendor = "ydb"
    display_name = "YDB"
    # This dictionary maps Field objects to their associated YDB column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        "AutoField": "Serial",
        "BigAutoField": "BigSerial",
        "BooleanField": "Bool",
        "CharField": "Utf8",  # TODO: make the method limit the number of characters
        # Date32/Timestamp64 are signed and wide-range, so dates before 1970
        # round-trip; Timestamp64 keeps microsecond precision.
        "DateField": "Date32",
        "DateTimeField": "Timestamp64",
        # YDB has no time type; store the time of day as Int64 microseconds
        # since midnight (introspects back as BigIntegerField).
        "TimeField": "Int64",
        # Decimal precision/scale come from the field's max_digits /
        # decimal_places (formatted by Field.db_type); YDB supports up to 35
        # digits (issue #82).
        "DecimalField": "Decimal(%(max_digits)s, %(decimal_places)s)",
        "DurationField": "Interval",
        "FloatField": "Float",
        "DoubleField": "Double",
        "IntegerField": "Int32",
        "BigIntegerField": "Int64",
        "NullBooleanField": "optional<Bool>",
        "PositiveIntegerField": "Uint32",
        "PositiveBigIntegerField": "Uint64",
        "PositiveSmallIntegerField": "Uint16",
        "SmallAutoField": "SmallSerial",
        "SmallIntegerField": "Int16",
        "TextField": "Utf8",
        "UUIDField": "UUID",
        "JSONField": "Json",
        "EnumField": "Enum",
        # TODO: Add validation for string related fields
        # FileField/ImageField store a text path, not raw bytes, so Utf8.
        "FileField": "Utf8",
        "FilePathField": "Utf8",
        "IPAddressField": "Utf8",
        "EmailField": "Utf8",
        "GenericIPAddressField": "Utf8",
        "SlugField": "Utf8",
        "BinaryField": "String",
    }

    # YDB's LIKE/ILIKE use '~' as the ESCAPE character: YQL rejects the SQL
    # default '\' (and '%'/'_') in the ESCAPE clause. The escaped values are
    # produced by DatabaseOperations.prep_for_like_query.
    operators = {
        "exact": "= %s",
        "iexact": "REGEXP '(?i)(' || %s || ')$'",
        "contains": "LIKE %s ESCAPE '~'",
        "icontains": "ILIKE %s ESCAPE '~'",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s ESCAPE '~'",
        "endswith": "LIKE %s ESCAPE '~'",
        "istartswith": "ILIKE %s ESCAPE '~'",
        "iendswith": "ILIKE %s ESCAPE '~'",
        "and": "AND",
        "or": "OR",
        "in": "IN (%s)",
        "between": "BETWEEN %s AND %s",
        "isnull": "IS NULL",
        "regex": "REGEXP %s",
        "iregex": "REGEXP '(?i)' || %s",
    }

    # Used when the right-hand side of a pattern lookup is an expression (e.g.
    # a column reference or a transform such as Substr) rather than a plain
    # value. Django fills pattern_esc into pattern_ops and the expression into
    # pattern_esc via str.format(); '%%' survives the final '%'-formatting in
    # Lookup.as_sql as a single '%' wildcard. YDB has no SQL REPLACE(), so the
    # special characters ('~', '%', '_') are escaped with String::ReplaceAll,
    # consistently with prep_for_like_query and ESCAPE '~'.
    # Unicode::ReplaceAll operates on Utf8 (String::ReplaceAll is String-only
    # and rejects a Utf8 expression). The Utf8 (``u``) literals keep ``||`` and
    # the left-hand Utf8 column/expression on the same operand type. A single
    # ``%`` is used (not the SQL-standard doubled ``%%``): this backend resolves
    # parameters by name and never ``%``-formats the assembled query, so ``%%``
    # would reach YDB doubled and break the literal-percent escaping.
    # The expression is COALESCEd to a non-optional Utf8: an expression over a
    # nullable column is Optional<Utf8>, and YQL's LIKE rejects an Optional
    # pattern (issue #91). A NULL right-hand side then yields an empty pattern
    # (match-all), which the pattern-lookup as_sql override in operations.py
    # corrects with a trailing "IS NOT NULL" guard so a NULL excludes the row.
    pattern_esc = (
        "Unicode::ReplaceAll(Unicode::ReplaceAll(Unicode::ReplaceAll("
        "COALESCE({}, ''u), '~'u, '~~'u), '%'u, '~%'u), '_'u, '~_'u)"
    )
    pattern_ops = {
        "contains": "LIKE '%'u || {} || '%'u ESCAPE '~'",
        "icontains": "ILIKE '%'u || {} || '%'u ESCAPE '~'",
        "startswith": "LIKE {} || '%'u ESCAPE '~'",
        "istartswith": "ILIKE {} || '%'u ESCAPE '~'",
        "endswith": "LIKE '%'u || {} ESCAPE '~'",
        "iendswith": "ILIKE '%'u || {} ESCAPE '~'",
    }

    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations
    validation_class = DatabaseValidation

    # def get_driver(self):
    #     return self.connection._driver

    def get_table_names(self):
        # Introspection may be the first database operation in a request (e.g.
        # `flush`/`migrate`), so make sure the underlying connection is open
        # before reaching into it.
        self.ensure_connection()
        return self.connection.get_table_names()

    def get_describe(self, table_name):
        self.ensure_connection()
        return self.connection.describe(table_name)

    @staticmethod
    def _parse_database_version(version):
        if isinstance(version, bytes):
            version = version.decode("utf-8")

        if version == "main":
            return ("main",)

        parsed_version = tuple(int(part) for part in re.findall(r"\d+", version))
        return parsed_version or None

    def get_database_version(self):
        """
        Return a tuple of the database's version.
        E.g. for ydb_version "23.4.11", return (23, 4, 11) or for ydb_version
        from trunk return "main".
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                row = cursor.fetchone()
                if row:
                    return self._parse_database_version(row[0])
                return None
        except Error as e:
            logger.error(f"Error while getting version: {e}")
            raise

    def check_database_version_supported(self):
        """
        Raise an error if the database version isn't supported by this
        version of Django.
        """
        database_version = self.get_database_version()
        if (
            self.features.minimum_database_version is not None
            and database_version is not None
            and database_version != ("main",)
            and database_version < self.features.minimum_database_version
        ):
            db_version = ".".join(map(str, database_version))
            min_db_version = ".".join(map(str, self.features.minimum_database_version))
            error_msg = (
                f"{self.display_name} {min_db_version} or later is required "
                f"(found {db_version})."
            )

            raise NotSupportedError(error_msg)

    def get_connection_params(self):
        """
        Return a dict of parameters suitable for get_new_connection.
        """
        settings_dict = self.settings_dict

        if not settings_dict.get("HOST"):
            raise ImproperlyConfigured(
                "YDB host is not configured. Set 'HOST' in DATABASES."
            )
        if not settings_dict.get("PORT"):
            raise ImproperlyConfigured(
                "YDB port is not configured. Set 'PORT' in DATABASES."
            )
        if not settings_dict.get("DATABASE"):
            raise ImproperlyConfigured(
                "YDB database is not configured. Set 'DATABASE' in DATABASES."
            )

        options = dict(settings_dict.get("OPTIONS", {}))
        isolation_level = options.pop("isolation_level", None)

        conn_params = {
            "host": settings_dict["HOST"],
            "port": settings_dict["PORT"],
            "database": settings_dict["DATABASE"],
            **options,
        }

        if isolation_level is not None:
            conn_params["isolation_level"] = _normalize_isolation_level(isolation_level)
        if settings_dict.get("CREDENTIALS"):
            conn_params["credentials"] = settings_dict["CREDENTIALS"]
        if settings_dict.get("ROOT_CERTIFICATES_PATH"):
            conn_params["root_certificates_path"] = settings_dict[
                "ROOT_CERTIFICATES_PATH"
            ]

        return conn_params

    def get_new_connection(self, conn_params):
        """
        Open a connection to the database.
        """
        isolation_level = conn_params.pop("isolation_level", None)
        try:
            logger.debug(f"Connecting to YDB with params: {conn_params}")
            connection = Database.connect(**conn_params)
            logger.info("Successfully connected to YDB.")
        except DatabaseError as e:
            logger.error(f"Failed to connect to YDB: {e}")
            msg = f"Failed to connect to YDB: {e}"
            raise OperationalError(msg) from e
        else:
            # Set the transaction mode for the connection. ``_set_autocommit``
            # keeps driving ``interactive_transaction`` from there on, so only
            # the tx mode needs to persist. Read-only modes (snapshot/online/
            # stale) accept reads only; writes are rejected by YDB.
            if isolation_level is not None:
                connection.set_isolation_level(isolation_level)
            return connection

    def create_cursor(self, name=None):
        """
        Create a cursor. Assume that a connection is established.
        """
        return self.connection.cursor()

    def _set_autocommit(self, autocommit):
        """
        Enable or disable autocommit.

        Disabling autocommit (entering ``transaction.atomic()``) opens an
        interactive YDB transaction; Django then drives ``commit()`` /
        ``rollback()`` on exit. Re-enabling it returns to per-statement
        autocommit. YDB has no savepoints, so nested atomic blocks are not
        isolated (see ``uses_savepoints = False``).
        """
        conn = self.connection
        if autocommit:
            conn.interactive_transaction = False
        else:
            conn.interactive_transaction = True
            conn.begin()

    def is_usable(self):
        """
        Test if the database connection is usable.

        This method may assume that self.connection is not None.

        Actual implementations should take care not to raise exceptions
        as that may prevent Django from recycling unusable connections.
        """
        if self.connection is None:
            return False
        try:
            with self.create_cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.rowcount == 1
        except DatabaseError as e:
            logger.warning(f"Connection is not usable: {e}")
            return False
