import unittest
from django.db import connections
from django.test import TestCase
from django.conf import settings
from ydb_backend.backend.base import DatabaseWrapper

TEST_YDB_SETTINGS = {
    'ENGINE': 'ydb',
    'ENDPOINT': 'grpc://localhost:2136',
    'DATABASE': '/local',
    'OPTIONS': {
        'credentials': None,
    },
}


class TestDatabaseWrapper(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Переопределяем настройки базы данных для тестов
        settings.DATABASES['default'] = TEST_YDB_SETTINGS
        cls.connection = connections['default']
        cls.db_wrapper = DatabaseWrapper(connections['default'].settings_dict)

    @classmethod
    def tearDownClass(cls):
        # Закрываем соединение после тестов
        if hasattr(cls, 'connection') and cls.connection:  # Проверяем, существует ли connection
            cls.connection.close()
        super().tearDownClass()

    def test_get_connection_params(self):
        """Тест метода get_connection_params."""
        conn_params = self.db_wrapper.get_connection_params()
        self.assertEqual(conn_params['endpoint'], TEST_YDB_SETTINGS['ENDPOINT'])
        self.assertEqual(conn_params['database'], TEST_YDB_SETTINGS['DATABASE'])

    def test_get_new_connection(self):
        """Тест метода get_new_connection."""
        conn_params = self.db_wrapper.get_connection_params()
        connection = self.db_wrapper.get_new_connection(conn_params)
        self.assertIsNotNone(connection)

    def test_create_cursor(self):
        """Тест метода create_cursor."""
        conn_params = self.db_wrapper.get_connection_params()
        self.db_wrapper.get_new_connection(conn_params)
        cursor = self.db_wrapper.create_cursor()
        self.assertIsNotNone(cursor)
        self.assertTrue(hasattr(cursor, 'execute'))
        # select 1

    def test_is_usable(self):
        """Тест метода is_usable."""
        conn_params = self.db_wrapper.get_connection_params()
        self.db_wrapper.get_new_connection(conn_params)
        self.assertTrue(self.db_wrapper.is_usable())

    def test_get_database_version(self):
        """Тест метода get_database_version."""
        version = self.db_wrapper.get_database_version()
        self.assertIsNotNone(version)
        self.assertIsInstance(version, tuple)
        self.assertTrue(len(version) >= 3)  # Версия должна быть в формате (major, minor, patch)

    def test_set_autocommit(self):
        """Тест метода _set_autocommit."""
        # Метод _set_autocommit не должен вызывать ошибок
        self.db_wrapper._set_autocommit(True)
        self.db_wrapper._set_autocommit(False)


if __name__ == '__main__':
    unittest.main()
