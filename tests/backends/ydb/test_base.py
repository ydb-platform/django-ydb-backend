from django.db import connection
from django.test import SimpleTestCase


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
