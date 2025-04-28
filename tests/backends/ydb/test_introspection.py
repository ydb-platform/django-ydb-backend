from django.db import connection
from django.test import TestCase
from ydb_backend.backend.introspection import FieldInfo
from ydb_backend.backend.introspection import TableInfo


class TestDatabaseIntrospection(TestCase):
    databases = {"default"}

    def test_get_field_type(self):
        self.assertEqual(
            connection.introspection.get_field_type("AutoField", ""),
            "SERIAL",
        )
        self.assertEqual(
            connection.introspection.get_field_type("PositiveIntegerField", ""),
            "Uint32",
        )
        self.assertEqual(
            connection.introspection.get_field_type("NullBooleanField", ""),
            "optional<Bool>",
        )
        self.assertEqual(
            connection.introspection.get_field_type("UUIDField", ""),
            "UUID",
        )

    def test_table_names(self):
        result = connection.introspection.table_names(include_views=True)
        self.assertIn("backends_tag", result)
        self.assertIn("backends_person", result)

    def test_get_table_description(self):
        expected_result = [
            FieldInfo(
                name="first_name",
                type_code="Utf8",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=None,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="last_name",
                type_code="Utf8",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=None,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="id",
                type_code="Int32",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=None,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="is_man",
                type_code="Bool?",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=None,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="about",
                type_code="String",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=None,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="age",
                type_code="Uint64",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=None,
                default=None,
                collation=None,
            ),
        ]

        with connection.cursor() as cursor:
            result = connection.introspection.get_table_description(
                cursor, "backends_person"
            )

        self.assertEqual(result, expected_result)

    def test_get_table_list(self):
        backends_person = TableInfo(name="backends_person", type="t")
        backends_tag = TableInfo(name="backends_tag", type="t")

        with connection.cursor() as cursor:
            result = connection.introspection.get_table_list(cursor)

        self.assertIn(backends_tag, result)
        self.assertIn(backends_person, result)

    def test_get_sequences(self):
        expected_result = [
            {"table_name": "backends_person", "column_name": "first_name"},
            {"table_name": "backends_person", "column_name": "last_name"},
            {"table_name": "backends_person", "column_name": "id"},
            {"table_name": "backends_person", "column_name": "is_man"},
            {"table_name": "backends_person", "column_name": "about"},
            {"table_name": "backends_person", "column_name": "age"},
        ]

        with connection.cursor() as cursor:
            result = connection.introspection.get_sequences(
                cursor, "backends_person", None
            )

        self.assertEqual(result, expected_result)

    def test_get_constraints(self):
        # TODO: Try to use model with indexes
        expected_result = {
            "primary_key": {
                "columns": ["id"],
                "primary_key": True,
                "unique": True,
                "foreign_key": None,
                "check": False,
                "index": True,
                "type": None,
            }
        }

        with connection.cursor() as cursor:
            result = connection.introspection.get_constraints(cursor, "backends_person")

        self.assertEqual(result, expected_result)

    def test_get_primary_key_columns(self):
        with connection.cursor() as cursor:
            result = connection.introspection.get_primary_key_columns(
                cursor, "backends_keymodel"
            )

        self.assertEqual(['id'], result)
