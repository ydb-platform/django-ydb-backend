from types import SimpleNamespace

from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import NotSupportedError
from django.test import SimpleTestCase
from ydb_backend.backend import base
from ydb_backend.backend.base import DatabaseWrapper
from ydb_dbapi import IsolationLevel


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


class TestConnectionParams(SimpleTestCase):
    @staticmethod
    def params(**settings):
        return DatabaseWrapper.get_connection_params(
            SimpleNamespace(settings_dict=settings)
        )

    def test_missing_host_raises(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "host"):
            self.params(PORT="2136", DATABASE="/local")

    def test_missing_port_raises(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "port"):
            self.params(HOST="localhost", DATABASE="/local")

    def test_missing_database_raises(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "database"):
            self.params(HOST="localhost", PORT="2136")

    def test_options_credentials_and_certificates_forwarded(self):
        params = self.params(
            HOST="localhost",
            PORT="2136",
            DATABASE="/local",
            OPTIONS={"ydb_table_path_prefix": "/local/x"},
            CREDENTIALS="token",
            ROOT_CERTIFICATES_PATH="/certs/ca.pem",
        )
        self.assertEqual(params["host"], "localhost")
        self.assertEqual(params["ydb_table_path_prefix"], "/local/x")
        self.assertEqual(params["credentials"], "token")
        self.assertEqual(params["root_certificates_path"], "/certs/ca.pem")

    def test_no_isolation_level_by_default(self):
        params = self.params(HOST="localhost", PORT="2136", DATABASE="/local")
        self.assertNotIn("isolation_level", params)

    def test_isolation_level_mapped_to_enum(self):
        params = self.params(
            HOST="localhost",
            PORT="2136",
            DATABASE="/local",
            OPTIONS={"isolation_level": "snapshot readonly"},
        )
        self.assertEqual(params["isolation_level"], IsolationLevel.SNAPSHOT_READONLY)

    def test_isolation_level_normalization_is_lenient(self):
        for value in ("SERIALIZABLE", "serializable", "Serializable"):
            params = self.params(
                HOST="localhost",
                PORT="2136",
                DATABASE="/local",
                OPTIONS={"isolation_level": value},
            )
            self.assertEqual(params["isolation_level"], IsolationLevel.SERIALIZABLE)
        # Enum member spelling (underscores) is accepted too.
        params = self.params(
            HOST="localhost",
            PORT="2136",
            DATABASE="/local",
            OPTIONS={"isolation_level": "online_readonly_inconsistent"},
        )
        self.assertEqual(
            params["isolation_level"],
            IsolationLevel.ONLINE_READONLY_INCONSISTENT,
        )

    def test_isolation_level_accepts_enum_instance(self):
        params = self.params(
            HOST="localhost",
            PORT="2136",
            DATABASE="/local",
            OPTIONS={"isolation_level": IsolationLevel.STALE_READONLY},
        )
        self.assertEqual(params["isolation_level"], IsolationLevel.STALE_READONLY)

    def test_unknown_isolation_level_raises(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "isolation_level"):
            self.params(
                HOST="localhost",
                PORT="2136",
                DATABASE="/local",
                OPTIONS={"isolation_level": "repeatable read"},
            )

    def test_is_usable_false_without_connection(self):
        self.assertFalse(DatabaseWrapper.is_usable(SimpleNamespace(connection=None)))


class TestNewConnectionIsolationLevel(SimpleTestCase):
    def test_isolation_level_applied_and_not_forwarded_to_connect(self):
        recorded = {}

        class FakeConnection:
            def set_isolation_level(self, level):
                recorded["level"] = level

        def fake_connect(**kwargs):
            recorded["connect_kwargs"] = kwargs
            return FakeConnection()

        conn_params = {
            "host": "localhost",
            "port": "2136",
            "database": "/local",
            "isolation_level": IsolationLevel.SNAPSHOT_READONLY,
        }
        original_connect = base.Database.connect
        base.Database.connect = fake_connect
        try:
            DatabaseWrapper.get_new_connection(SimpleNamespace(), conn_params)
        finally:
            base.Database.connect = original_connect

        self.assertEqual(recorded["level"], IsolationLevel.SNAPSHOT_READONLY)
        self.assertNotIn("isolation_level", recorded["connect_kwargs"])


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
