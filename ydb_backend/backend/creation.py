from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        # try:
        #     print("хуй")
        #     cursor.execute_scheme("CREATE DATABASE %(dbname)s %(suffix)s" % parameters)
        # except Exception as e:
        #     self.log(f"Error creating test database: {e}")
        #     if not keepdb:
        #         raise
        #     self.log("Failed to create test database, it may already exist.")
        return None

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        test_database_name = self.get_test_db_clone_settings(suffix)["NAME"]

        test_db_params = {
            "dbname": self.connection.ops.quote_name(test_database_name),
            "suffix": self.sql_table_creation_suffix(),
        }

        if verbosity >= 1:
            self.log(f"Creating test database '{test_database_name}'...")

        try:
            with self.connection.cursor() as cursor:
                self._execute_create_test_db(cursor, test_db_params, keepdb)
        except Exception as e:
            self.log(f"{e} occurred")
            if not keepdb:
                raise
            self.log(f"Test database '{test_database_name}' already exists.")

        return test_database_name

    def _destroy_test_db(self, test_database_name, verbosity):
        if verbosity >= 1:
            self.log(f"Destroying test database '{test_database_name}'...")

        with self.connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE {test_database_name}")
