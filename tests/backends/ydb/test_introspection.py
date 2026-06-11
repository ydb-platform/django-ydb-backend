from django.db import connection
from django.test import TestCase
from ydb_backend.backend.introspection import FieldInfo
from ydb_backend.backend.introspection import TableInfo


class TestDatabaseIntrospection(TestCase):
    databases = {"default"}

    def test_get_yql_type(self):
        # Forward mapping (Django internal type -> YQL type) used to build
        # DECLARE statements in the insert/upsert compilers.
        self.assertEqual(
            connection.introspection.get_yql_type("AutoField"),
            "Int32",
        )
        self.assertEqual(
            connection.introspection.get_yql_type("PositiveIntegerField"),
            "Uint32",
        )
        self.assertEqual(
            connection.introspection.get_yql_type("NullBooleanField"),
            "optional<Bool>",
        )
        self.assertEqual(
            connection.introspection.get_yql_type("UUIDField"),
            "UUID",
        )

    def test_get_field_type_reverse(self):
        # Reverse mapping (YDB type name -> Django field) used by introspection
        # and inspectdb.
        self.assertEqual(
            connection.introspection.get_field_type("Int32", None),
            "IntegerField",
        )
        self.assertEqual(
            connection.introspection.get_field_type("Uint32", None),
            "PositiveIntegerField",
        )
        self.assertEqual(
            connection.introspection.get_field_type("Bool", None),
            "BooleanField",
        )
        self.assertEqual(
            connection.introspection.get_field_type("UUID", None),
            "UUIDField",
        )
        self.assertEqual(
            connection.introspection.get_field_type("Decimal", None),
            "DecimalField",
        )
        # Unknown YDB types fall back to TextField so inspectdb keeps working.
        self.assertEqual(
            connection.introspection.get_field_type("Mystery", None),
            "TextField",
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
                null_ok=False,
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
                null_ok=False,
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
                null_ok=False,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="is_man",
                type_code="Bool",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=True,
                default=None,
                collation=None,
            ),
            FieldInfo(
                name="about",
                type_code="Utf8",
                display_size=None,
                internal_size=None,
                precision=None,
                scale=None,
                null_ok=False,
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
                null_ok=False,
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
        # Only the integer auto-increment primary key is reported as a
        # sequence, using Django's {'table', 'column'} contract.
        expected_result = [
            {"table": "backends_person", "column": "id"},
        ]

        with connection.cursor() as cursor:
            result = connection.introspection.get_sequences(
                cursor, "backends_person", None
            )

        self.assertEqual(result, expected_result)

    def test_get_sequences_skips_non_integer_pk(self):
        # compiler_product has a CharField primary key ("sku"), which is not an
        # auto-increment sequence.
        with connection.cursor() as cursor:
            result = connection.introspection.get_sequences(
                cursor, "compiler_product"
            )

        self.assertEqual(result, [])

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
                "orders": ["ASC"],
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

        self.assertEqual(["id"], result)

    def test_get_table_description_decimal_precision_scale(self):
        with connection.cursor() as cursor:
            result = connection.introspection.get_table_description(
                cursor, "type_floatingpointmodel"
            )

        decimal_field = next(f for f in result if f.name == "decimal_field")
        self.assertEqual(decimal_field.type_code, "Decimal")
        self.assertEqual(decimal_field.precision, 22)
        self.assertEqual(decimal_field.scale, 9)
        self.assertFalse(decimal_field.null_ok)

    def test_get_constraints_index_metadata(self):
        with connection.cursor() as cursor:
            result = connection.introspection.get_constraints(
                cursor, "backends_modelwithindexes"
            )

        index = result["single_idx_w_name"]
        self.assertEqual(index["columns"], ["single_idx_field_w_name"])
        # YDB secondary indexes are non-unique and ascending.
        self.assertFalse(index["unique"])
        self.assertFalse(index["primary_key"])
        self.assertTrue(index["index"])
        self.assertEqual(index["orders"], ["ASC"])
