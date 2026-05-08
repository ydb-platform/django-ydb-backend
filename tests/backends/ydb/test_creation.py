import os
from unittest.mock import MagicMock
from unittest.mock import patch

import ydb
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


class TestGetTestDbName(SimpleTestCase):
    def test_default_name_without_suffix(self):
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_TEST_DB_SUFFIX"}
        with patch.dict(os.environ, env, clear=True):
            base_name = connection.creation._get_test_db_name()
        with patch.dict(os.environ, {"DJANGO_TEST_DB_SUFFIX": "x"}):
            suffixed_name = connection.creation._get_test_db_name()
        self.assertEqual(suffixed_name, f"{base_name}_x")

    def test_suffix_appended_from_env(self):
        with patch.dict(os.environ, {"DJANGO_TEST_DB_SUFFIX": "ci42"}):
            name = connection.creation._get_test_db_name()
        self.assertTrue(name.endswith("_ci42"), name)

    def test_empty_suffix_not_appended(self):
        with patch.dict(os.environ, {"DJANGO_TEST_DB_SUFFIX": ""}):
            name_with_empty = connection.creation._get_test_db_name()
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_TEST_DB_SUFFIX"}
        with patch.dict(os.environ, env, clear=True):
            name_without = connection.creation._get_test_db_name()
        self.assertEqual(name_with_empty, name_without)


class TestDropTestTables(SimpleTestCase):
    def _make_prefixed_conn(self, table_names=None, get_table_names_error=None):
        mock_conn = MagicMock()
        if get_table_names_error is not None:
            mock_conn.get_table_names.side_effect = get_table_names_error
        else:
            mock_conn.get_table_names.return_value = table_names or []
        return mock_conn

    def _db_error(self):
        return connection.Database.DatabaseError("directory not found")

    def test_drops_all_existing_tables(self):
        mock_conn = self._make_prefixed_conn(["auth_user", "app_book"])
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(
            connection.creation,
            "_get_prefixed_connection",
            return_value=mock_conn,
        ):
            connection.creation._drop_test_tables("/local/test_db")

        self.assertEqual(mock_cursor.execute_scheme.call_count, 2)

    def test_handles_missing_directory_gracefully(self):
        mock_conn = self._make_prefixed_conn(get_table_names_error=self._db_error())

        with patch.object(
            connection.creation,
            "_get_prefixed_connection",
            return_value=mock_conn,
        ):
            connection.creation._drop_test_tables("/local/test_missing")

        mock_conn.close.assert_called_once()

    def test_handles_empty_directory(self):
        mock_conn = self._make_prefixed_conn(table_names=[])
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(
            connection.creation,
            "_get_prefixed_connection",
            return_value=mock_conn,
        ):
            connection.creation._drop_test_tables("/local/test_empty")

        mock_cursor.execute_scheme.assert_not_called()
        mock_conn.close.assert_called_once()

    def test_connection_closed_after_error(self):
        mock_conn = self._make_prefixed_conn(get_table_names_error=self._db_error())

        with patch.object(
            connection.creation,
            "_get_prefixed_connection",
            return_value=mock_conn,
        ):
            connection.creation._drop_test_tables("/local/test_db")

        mock_conn.close.assert_called_once()


class TestDestroyTestDb(SimpleTestCase):
    def _make_db_conn(self, remove_side_effect=None):
        mock_conn = MagicMock()
        if remove_side_effect is not None:
            scheme = mock_conn._driver.scheme_client
            scheme.remove_directory.side_effect = remove_side_effect
        return mock_conn

    def test_drops_tables_then_removes_directory(self):
        mock_conn = self._make_db_conn()
        call_order = []

        def track_drop(path):
            call_order.append("drop")

        def track_remove(path):
            call_order.append("remove")

        mock_conn._driver.scheme_client.remove_directory.side_effect = track_remove
        creation = connection.creation

        with (
            patch.object(creation, "_drop_test_tables", side_effect=track_drop),
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
        ):
            creation._destroy_test_db("test_ydb_db", verbosity=0)

        self.assertEqual(call_order, ["drop", "remove"])

    def test_handles_missing_directory_on_remove(self):
        error = ydb.SchemeError("path not found")
        mock_conn = self._make_db_conn(remove_side_effect=error)
        creation = connection.creation

        with (
            patch.object(creation, "_drop_test_tables"),
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
        ):
            creation._destroy_test_db("test_ydb_db", verbosity=0)

        mock_conn.close.assert_called_once()

    def test_connection_closed_even_if_remove_fails(self):
        mock_conn = self._make_db_conn(remove_side_effect=ydb.SchemeError("gone"))
        creation = connection.creation

        with (
            patch.object(creation, "_drop_test_tables"),
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
        ):
            creation._destroy_test_db("test_ydb_db", verbosity=0)

        mock_conn.close.assert_called_once()

    def test_uses_correct_path(self):
        mock_conn = self._make_db_conn()
        captured_paths = {}
        creation = connection.creation

        def capture_drop(path):
            captured_paths["drop"] = path

        def capture_remove(path):
            captured_paths["remove"] = path

        mock_conn._driver.scheme_client.remove_directory.side_effect = capture_remove

        with (
            patch.object(creation, "_drop_test_tables", side_effect=capture_drop),
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
        ):
            creation._destroy_test_db("test_ydb_db", verbosity=0)

        expected_path = "/local/test_ydb_db"
        self.assertEqual(captured_paths["drop"], expected_path)
        self.assertEqual(captured_paths["remove"], expected_path)


class TestExecuteCreateTestDb(SimpleTestCase):
    def test_keepdb_skips_drop(self):
        mock_conn = MagicMock()
        creation = connection.creation

        with (
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
            patch.object(creation, "_drop_test_tables") as mock_drop,
            patch.object(creation, "_set_test_table_path_prefix"),
        ):
            creation._execute_create_test_db(None, None, keepdb=True)

        mock_drop.assert_not_called()

    def test_no_keepdb_drops_tables(self):
        mock_conn = MagicMock()
        creation = connection.creation

        with (
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
            patch.object(creation, "_drop_test_tables") as mock_drop,
            patch.object(creation, "_set_test_table_path_prefix"),
        ):
            creation._execute_create_test_db(None, None, keepdb=False)

        mock_drop.assert_called_once()

    def test_creates_directory(self):
        mock_conn = MagicMock()
        creation = connection.creation

        with (
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
            patch.object(creation, "_drop_test_tables"),
            patch.object(creation, "_set_test_table_path_prefix"),
        ):
            creation._execute_create_test_db(None, None, keepdb=False)

        mock_conn._driver.scheme_client.make_directory.assert_called_once()

    def test_connection_closed_after_setup(self):
        mock_conn = MagicMock()
        creation = connection.creation

        with (
            patch.object(
                creation, "_get_database_connection", return_value=mock_conn
            ),
            patch.object(creation, "_drop_test_tables"),
            patch.object(creation, "_set_test_table_path_prefix"),
        ):
            creation._execute_create_test_db(None, None, keepdb=False)

        mock_conn.close.assert_called_once()
