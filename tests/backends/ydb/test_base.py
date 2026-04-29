from types import SimpleNamespace

from django.db import connection
from django.db.utils import NotSupportedError
from django.test import SimpleTestCase
from ydb_backend.backend.base import DatabaseWrapper


class TestDatabaseWrapper(SimpleTestCase):
    databases = {"default"}

    def test_get_database_version(self):
        version = connection.get_database_version()
        self.assertIsNotNone(version)

    def test_get_connection_params(self):
        params = connection.get_connection_params()
        self.assertIn("host", params)
        self.assertIn("port", params)
        self.assertIn("database", params)

    def test_get_new_connection(self):
        new_connection = connection.get_new_connection(
            connection.get_connection_params()
        )
        self.assertTrue(hasattr(new_connection, "cursor"))

    def test_create_cursor(self):
        with connection.cursor() as cursor:
            self.assertTrue(hasattr(cursor, "execute"))
            cursor.execute("SELECT 10")
            result = cursor.fetchone()
            self.assertEqual(result, (10,))

    def test_is_usable(self):
        self.assertTrue(connection.is_usable())


class TestDatabaseVersion(SimpleTestCase):
    def test_parse_numeric_database_version(self):
        version = DatabaseWrapper._parse_database_version(b"23.4.11-ydb")

        self.assertEqual(version, (23, 4, 11))

    def test_parse_stable_database_version(self):
        version = DatabaseWrapper._parse_database_version(b"stable-26-1-1-10")

        self.assertEqual(version, (26, 1, 1, 10))

    def test_parse_database_version_skips_string_literals(self):
        version = DatabaseWrapper._parse_database_version("release-25.2-ydb-7")

        self.assertEqual(version, (25, 2, 7))

    def test_parse_main_database_version(self):
        version = DatabaseWrapper._parse_database_version(b"main")

        self.assertEqual(version, ("main",))

    def test_parse_unknown_database_version(self):
        version = DatabaseWrapper._parse_database_version(b"unknown")

        self.assertIsNone(version)

    def test_check_database_version_supported_uses_numeric_comparison(self):
        wrapper = SimpleNamespace(
            display_name="YDB",
            features=SimpleNamespace(minimum_database_version=(20,)),
            get_database_version=lambda: (23, 4, 11),
        )

        DatabaseWrapper.check_database_version_supported(wrapper)

    def test_check_database_version_supported_rejects_old_version(self):
        wrapper = SimpleNamespace(
            display_name="YDB",
            features=SimpleNamespace(minimum_database_version=(20,)),
            get_database_version=lambda: (19, 9),
        )

        with self.assertRaisesMessage(
            NotSupportedError,
            "YDB 20 or later is required (found 19.9).",
        ):
            DatabaseWrapper.check_database_version_supported(wrapper)
