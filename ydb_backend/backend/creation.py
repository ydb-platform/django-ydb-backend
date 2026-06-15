import os
from abc import ABC

import django
import ydb
from django.conf import settings
from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation, ABC):
    """
    Encapsulate backends-specific differences pertaining to creation and
    destruction of the test database.
    """

    def _get_test_db_name(self):
        name = super()._get_test_db_name()
        suffix = os.environ.get("DJANGO_TEST_DB_SUFFIX", "")
        return f"{name}_{suffix}" if suffix else name

    def _get_test_database_path(self, test_database_name=None):
        test_database_name = test_database_name or self._get_test_db_name()
        if test_database_name.startswith("/"):
            return test_database_name

        database_path = self.connection.settings_dict["DATABASE"].rstrip("/")
        return f"{database_path}/{test_database_name}"

    def _set_test_table_path_prefix(self, test_database_path):
        for database_settings in (
            settings.DATABASES[self.connection.alias],
            self.connection.settings_dict,
        ):
            options = database_settings.setdefault("OPTIONS", {})
            options["ydb_table_path_prefix"] = test_database_path

    def _restore_table_path_prefix(self):
        old_ydb_table_path_prefix = getattr(
            self, "_old_ydb_table_path_prefix", None
        )
        for database_settings in (
            settings.DATABASES[self.connection.alias],
            self.connection.settings_dict,
        ):
            options = database_settings.setdefault("OPTIONS", {})
            if old_ydb_table_path_prefix is None:
                options.pop("ydb_table_path_prefix", None)
            else:
                options["ydb_table_path_prefix"] = old_ydb_table_path_prefix

    def _get_prefixed_connection(self, test_database_path):
        conn_params = self.connection.get_connection_params()
        conn_params["ydb_table_path_prefix"] = test_database_path
        return self.connection.Database.connect(**conn_params)

    def _get_database_connection(self):
        conn_params = self.connection.get_connection_params()
        conn_params.pop("ydb_table_path_prefix", None)
        return self.connection.Database.connect(**conn_params)

    def _drop_test_tables(self, test_database_path):
        connection = self._get_prefixed_connection(test_database_path)
        try:
            try:
                table_names = connection.get_table_names()
            except self.connection.Database.DatabaseError:
                return
            with connection.cursor() as cursor:
                for table_name in table_names:
                    quoted_name = self.connection.ops.quote_name(table_name)
                    cursor.execute_scheme(f"DROP TABLE {quoted_name};")
        finally:
            connection.close()

    def create_test_db(
        self, verbosity=1, autoclobber=False, serialize=True, keepdb=False
    ):
        self._old_ydb_table_path_prefix = self.connection.settings_dict.get(
            "OPTIONS", {}
        ).get("ydb_table_path_prefix")
        # Django 6.0 deprecated the ``serialize`` argument to create_test_db()
        # (serialization moved to serialize_test_db()); passing it raises
        # RemovedInDjango70Warning, which the bundled test runner escalates to
        # an error. Only forward it on versions that still accept it.
        if django.VERSION >= (6, 0):
            return super().create_test_db(
                verbosity=verbosity, autoclobber=autoclobber, keepdb=keepdb
            )
        return super().create_test_db(verbosity, autoclobber, serialize, keepdb)

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        test_database_path = self._get_test_database_path()
        connection = self._get_database_connection()
        try:
            connection._driver.scheme_client.make_directory(test_database_path)
            if not keepdb:
                self._drop_test_tables(test_database_path)
        finally:
            connection.close()

        self._set_test_table_path_prefix(test_database_path)
        return test_database_path

    def _destroy_test_db(self, test_database_name, verbosity):
        test_database_path = self._get_test_database_path(test_database_name)
        self._drop_test_tables(test_database_path)
        connection = self._get_database_connection()
        try:
            connection._driver.scheme_client.remove_directory(test_database_path)
        except ydb.SchemeError:
            pass
        finally:
            connection.close()

    def destroy_test_db(
        self, old_database_name=None, verbosity=1, keepdb=False, suffix=None
    ):
        try:
            super().destroy_test_db(old_database_name, verbosity, keepdb, suffix)
        finally:
            self._restore_table_path_prefix()
