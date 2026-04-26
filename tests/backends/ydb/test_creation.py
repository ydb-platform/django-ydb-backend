from django.db import connection
from django.test import SimpleTestCase


class TestDatabaseCreation(SimpleTestCase):
    def test_get_test_database_path_uses_database_setting(self):
        test_database_path = connection.creation._get_test_database_path("test_ydb_db")

        self.assertEqual(test_database_path, "/local/test_ydb_db")

    def test_get_test_database_path_allows_absolute_path(self):
        test_database_path = connection.creation._get_test_database_path(
            "/local/custom_test"
        )

        self.assertEqual(test_database_path, "/local/custom_test")

    def test_restore_table_path_prefix_removes_test_prefix(self):
        creation = connection.creation
        options = connection.settings_dict.setdefault("OPTIONS", {})
        old_prefix = options.pop("ydb_table_path_prefix", None)

        try:
            creation._old_ydb_table_path_prefix = None
            creation._set_test_table_path_prefix("/local/test_ydb_db")

            self.assertEqual(options["ydb_table_path_prefix"], "/local/test_ydb_db")

            creation._restore_table_path_prefix()

            self.assertNotIn("ydb_table_path_prefix", options)
        finally:
            if old_prefix is not None:
                options["ydb_table_path_prefix"] = old_prefix
