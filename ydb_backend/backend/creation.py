from abc import ABC

from django.db.backends.base.creation import BaseDatabaseCreation


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
        # TODO: not supported in YDB, need to check details
        # self.connection._driver.scheme_client.remove_directory("/local/test")
        return None
