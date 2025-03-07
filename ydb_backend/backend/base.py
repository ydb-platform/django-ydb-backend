from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.base import logger
from django.db.utils import DatabaseError
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


def db_api_version():
    if hasattr(Database, "version"):
        version = Database.version.VERSION.split(".")
        return tuple(map(int, version))
    return 0, 0, 0


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = "ydb"
    display_name = "YDB"
    # This dictionary maps Field objects to their associated YDB column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        "AutoField": "Int64",
        "BigAutoField": "Int64",
        "BinaryField": "String",
        "BooleanField": "Bool",
        "CharField": "String",
        "DateField": "Date",
        "DateTimeField": "Datetime",
        "DecimalField": "Decimal",
        "DurationField": "Interval",
        "FileField": "String",
        "FilePathField": "String",
        "FloatField": "Double",
        "IntegerField": "Int32",
        "BigIntegerField": "Int64",
        "IPAddressField": "String",
        "GenericIPAddressField": "String",
        "NullBooleanField": "Bool",
        "OneToOneField": "Int64",
        "PositiveIntegerField": "Uint32",
        "PositiveBigIntegerField": "Int64",
        "PositiveSmallIntegerField": "Uint16",
        "SlugField": "String",
        "SmallAutoField": "Int32",
        "SmallIntegerField": "Int16",
        "TextField": "String",
        "TimeField": "Timestamp",
        "UUIDField": "String",
    }

    operators = {
        "exact": "= %s",
        "iexact": "ILIKE %s",
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
        "iregex": "REGEXP %s",
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

    def get_table_names(self):
        return self.connection.get_table_names()

    def get_database_version(self):
        """
        Return a tuple of the database's version.
        E.g. for ydb_version "23.4.11", return (23, 4, 11).
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                row = cursor.fetchone()
                if row:
                    parts = row[0].decode("utf-8").split("-")[0].split(".")
                    return tuple(int(part) for part in parts)
                return None
        except (OperationalError, ProgrammingError) as e:
            logger.warning(
                f"Failed to get database version: {e}. Falling back to driver version."
            )
            return db_api_version()
        except DatabaseError as e:
            logger.error(f"Database error while getting version: {e}")
            raise

    def get_connection_params(self):
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

        return conn_params

    def get_new_connection(self, conn_params):
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
        return self.connection.cursor()

    def _set_autocommit(self, autocommit):
        pass

    def is_usable(self):
        if self.connection is None:
            return False
        try:
            with self.create_cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.rowcount == 1
        except DatabaseError as e:
            logger.warning(f"Connection is not usable: {e}")
            return False
