from abc import ABC

from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation, ABC):
    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        # TODO: not supported in YDB, need to check details
        return "/local"

    def _destroy_test_db(self, test_database_name, verbosity):
        # TODO: not supported in YDB, need to check details
        return None
