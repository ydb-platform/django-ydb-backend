# import unittest
from django.test import TestCase
from unittest.mock import patch
from ydb_backend.backend.base import DatabaseWrapper, ydb_version
from django.db.utils import OperationalError, ProgrammingError


class TestDatabaseWrapper(TestCase):
    @patch('ydb_backend.backend.base.DatabaseWrapper.get_database_version')
    def test_get_database_version(self, mock_get_version):
        mock_get_version.return_value = '0.0.31'
        wrapper = DatabaseWrapper({})
        self.assertEqual(wrapper.get_database_version(), '0.0.31')

    @patch('ydb_backend.backend.base.DatabaseWrapper.cursor')
    def test_get_database_version_with_exception(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.execute.side_effect = OperationalError("Connection error")
        wrapper = DatabaseWrapper({})
        version = wrapper.get_database_version()
        self.assertEqual(version, ydb_version())

    @patch('ydb_backend.backend.base.DatabaseWrapper.cursor')
    def test_get_database_version_fallback(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.execute.side_effect = ProgrammingError("SQL error")
        wrapper = DatabaseWrapper({})
        version = wrapper.get_database_version()
        self.assertEqual(version, ydb_version())

    @patch('ydb_backend.backend.base.DatabaseWrapper.cursor')
    def test_get_database_version_success(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = ['23.4.11']
        wrapper = DatabaseWrapper({})
        version = wrapper.get_database_version()
        self.assertEqual(version, '23.4.11')
