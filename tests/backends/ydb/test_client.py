"""Tests for ydb_backend.backend.client.

These verify the dbshell command line is assembled from the connection settings
(host/port/database/credentials, then any extra parameters). No database is
needed.
"""

from django.test import SimpleTestCase
from ydb_backend.backend.client import DatabaseClient


class ClientArgsTests(SimpleTestCase):
    def args_env(self, settings_dict, parameters=None):
        return DatabaseClient.settings_to_cmd_args_env(
            settings_dict, parameters or []
        )

    def test_full_settings(self):
        args, env = self.args_env(
            {
                "HOST": "localhost",
                "PORT": "2136",
                "DATABASE": "/local",
                "CREDENTIALS": "token",
            }
        )
        self.assertEqual(
            args,
            [
                "ydb-client",
                "--host", "localhost",
                "--port", "2136",
                "--database", "/local",
                "--credentials", "token",
            ],
        )
        self.assertEqual(env, {})

    def test_empty_settings(self):
        args, env = self.args_env({})
        self.assertEqual(args, ["ydb-client"])
        self.assertEqual(env, {})

    def test_partial_settings(self):
        args, _ = self.args_env({"HOST": "h", "DATABASE": "/db"})
        self.assertEqual(args, ["ydb-client", "--host", "h", "--database", "/db"])

    def test_extra_parameters_are_appended(self):
        args, _ = self.args_env({"HOST": "h"}, parameters=["-q", "SELECT 1"])
        self.assertEqual(args, ["ydb-client", "--host", "h", "-q", "SELECT 1"])
