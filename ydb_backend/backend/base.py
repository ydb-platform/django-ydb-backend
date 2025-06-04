from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.base import logger
from django.db.utils import DatabaseError
from django.db.utils import NotSupportedError
from django.db.utils import OperationalError
from django.db.utils import ProgrammingError

try:
    import ydb_dbapi as Database  # noqa: N812
except ImportError:
    Database = None

if Database is None:
    raise ImproperlyConfigured(
        "Error loading ydb_dbapi module. Install it using 'pip install ydb_dbapi'."
    )

from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor
from .validation import DatabaseValidation


def _db_api_version():
    if hasattr(Database, "version"):
        version = Database.version.VERSION.split(".")
        return tuple(map(int, version))
    return 0, 0, 0


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
        "DateField": "Date",
        "DateTimeField": "Datetime",
        "DecimalField": "Decimal(22, 9)",
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
        "FileField": "String",
        "FilePathField": "Utf8",
        "IPAddressField": "Utf8",
        "EmailField": "Utf8",
        "GenericIPAddressField": "Utf8",
        "SlugField": "Utf8",
        "BinaryField": "String",
    }

    operators = {
        "exact": "= %s",
        "iexact": "REGEXP '(?i)(' || %s || ')$'",
        "contains": "LIKE %s",
        "icontains": "ILIKE %s",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s",
        "endswith": "LIKE %s",
        "istartswith": "ILIKE %s",
        "iendswith": "ILIKE %s",
        "and": "AND",
        "or": "OR",
        "in": "IN (%s)",
        "between": "BETWEEN %s AND %s",
        "isnull": "IS NULL",
        "regex": "REGEXP %s",
        "iregex": "REGEXP '(?i)' || %s",
    }

    # The patterns below are used to generate SQL pattern lookup clauses when
    # the right-hand side of the lookup isn't a raw string (it might be an expression
    # or the result of a bilateral transformation).
    # In those cases, special characters for LIKE operators (e.g. \, *, _) should be
    # escaped on database side.
    #
    # Note: we use str.format() here for readability as '%' is used as a wildcard for
    # the LIKE operator.
    pattern_esc = (
        r"REPLACE(REPLACE(REPLACE({}, E'\\', E'\\\\'), E'%%', E'\\%%'), E'_', E'\\_')"
    )
    pattern_ops = {
        "contains": "LIKE '%%%s%%' ESCAPE '\\'",
        "icontains": "ILIKE '%%%s%%' ESCAPE '\\'",
        "startswith": "LIKE '%s%%' ESCAPE '\\'",
        "istartswith": "ILIKE '%s%%' ESCAPE '\\'",
        "endswith": "LIKE '%%%s' ESCAPE '\\'",
        "iendswith": "ILIKE '%%%s' ESCAPE '\\'",
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
        return self.connection.get_table_names()

    def get_describe(self, table_name):
        return self.connection.describe(table_name)

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
                    parts = row[0].decode("utf-8").split("-")[0].split(".")
                    return tuple(part for part in parts)
                return None
        except (OperationalError, ProgrammingError) as e:
            logger.warning(
                f"Failed to get database version: {e}. "
                f"Falling back to driver version."
            )
            return _db_api_version()
        except DatabaseError as e:
            logger.error(f"Database error while getting version: {e}")
            raise

    def check_database_version_supported(self):
        """
        Raise an error if the database version isn't supported by this
        version of Django.
        """
        if (
                self.features.minimum_database_version is not None
                and self.get_database_version() != ("main",)
                and self.get_database_version() < self.features.minimum_database_version
        ):
            db_version = ".".join(map(str, self.get_database_version()))
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

        conn_params = {
            "host": settings_dict["HOST"],
            "port": settings_dict["PORT"],
            "database": settings_dict["DATABASE"],
            **settings_dict.get("OPTIONS", {}),
        }
        if settings_dict.get("NAME"):
            conn_params["name"] = settings_dict["NAME"]
        if settings_dict.get("CREDENTIALS"):
            conn_params["credentials"] = settings_dict["CREDENTIALS"]
        if settings_dict.get("ROOT_CERTIFICATES"):
            conn_params["root_certificates"] = settings_dict["ROOT_CERTIFICATES"]
        if settings_dict.get("CONNECTION_TIMEOUT"):
            conn_params["connection_timeout"] = settings_dict["CONNECTION_TIMEOUT"]
        if settings_dict.get("REQUEST_TIMEOUT"):
            conn_params["request_timeout"] = settings_dict["REQUEST_TIMEOUT"]
        if settings_dict.get("TIME_ZONE"):
            conn_params["time_zone"] = settings_dict["TIME_ZONE"]

        return conn_params

    def get_new_connection(self, conn_params):
        """
        Open a connection to the database.
        """
        try:
            logger.debug(f"Connecting to YDB with params: {conn_params}")
            connection = Database.connect(**conn_params)
            logger.info("Successfully connected to YDB.")
        except DatabaseError as e:
            logger.error(f"Failed to connect to YDB: {e}")
            msg = f"Failed to connect to YDB: {e}"
            raise OperationalError(msg) from e
        else:
            return connection

    def create_cursor(self, name=None):
        """
        Create a cursor. Assume that a connection is established.
        """
        return self.connection.cursor()

    def _set_autocommit(self, autocommit):
        """
        Backend-specific implementation to enable or disable autocommit.
        """

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
