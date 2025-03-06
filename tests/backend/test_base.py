from django.db import connection
from django.test import SimpleTestCase


class TestDatabaseWrapper(SimpleTestCase):
    databases = {"default"}

    def test_get_database_version(self):
        """
        Тест для метода get_database_version.
        Проверяет, что метод возвращает версию базы данных YDB.
        """
        version = connection.get_database_version()
        self.assertIsNotNone(version)

    def test_get_connection_params(self):
        """
        Тест для метода get_connection_params.
        Проверяет, что метод возвращает правильные параметры подключения к базе данных YDB.
        """
        params = connection.get_connection_params()
        self.assertIn('endpoint', params)
        self.assertIn('database', params)
        self.assertIn('credentials', params)

    def test_get_new_connection(self):
        """
        Тест для метода get_new_connection.
        Проверяет, что метод создаёт новое соединение с базой данных YDB.
        """
        new_connection = connection.get_new_connection(connection.get_connection_params())
        self.assertTrue(hasattr(new_connection, 'cursor'))

    def test_create_cursor(self):
        """
        Тест для метода create_cursor.
        Проверяет, что метод создаёт новый курсор для соединения с базой данных YDB.
        """
        cursor = connection.create_cursor()
        self.assertTrue(hasattr(cursor, 'execute'))

    def test_is_usable(self):
        """
        Тест для метода is_usable.
        Проверяет, что метод определяет, доступно ли соединение с базой данных YDB.
        """
        self.assertTrue(connection.is_usable())
