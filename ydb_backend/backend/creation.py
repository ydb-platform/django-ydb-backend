import logging
from abc import ABC

from django.db import DatabaseError
from django.db import InterfaceError
from django.db import OperationalError
from django.db import ProgrammingError
from django.db import connection
from django.db.backends.base.creation import BaseDatabaseCreation

logger = logging.getLogger("django_ydb_backend.ydb_backend.backend.creation")


class DatabaseCreation(BaseDatabaseCreation, ABC):
    """
    Encapsulate backends-specific differences pertaining to creation and
    destruction of the test database.
    """

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        # TODO: not supported in YDB, need to check details
        # cursor._connection.get_driver().scheme_client.make_directory("/local/test")
        return "/local"

    def _destroy_test_db(self, test_database_name, verbosity):
        qn = self.connection.ops.quote_name
        if verbosity >= 1:
            logger.debug("Cleaning up test database: %s", test_database_name)

        with self.connection.cursor() as cursor:
            try:
                tables = connection.introspection.table_names(include_views=True)

                for table in tables:
                    qn_table = qn(table)
                    try:
                        cursor.execute_scheme(f"DROP TABLE {qn_table};")
                        if verbosity >= 1:
                            logger.debug("Dropping table: %s", table)
                    except (DatabaseError, OperationalError, ProgrammingError) as e:
                        if verbosity >= 1:
                            logger.debug("Failed to drop %s: %s", table, str(e))
            except (DatabaseError, OperationalError, InterfaceError) as e:
                if verbosity >= 1:
                    logger.debug("Could not fetch tables: %s", str(e))
