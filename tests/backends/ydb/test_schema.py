from django.db import connection
from django.db import migrations
from django.db import models
from django.db.models import Index
from django.db.models import TextField
from django.test import TransactionTestCase

from ..models import ModelWithIndexes
from ..models import MyModel
from ..models import OldNameModel
from ..models import SimpleModel


def _get_indexes():
    with connection.cursor() as cursor:
        table_name = "backends_modelwithindexes"
        constraints = connection.introspection.get_constraints(
            cursor, table_name
        )

    return [key for key, value in constraints.items() if value.get("index") is True]


class TestDatabaseSchema(TransactionTestCase):
    databases = {"default"}

    def test_create_model(self):
        class Triangle(models.Model):
            id = models.AutoField(primary_key=True)
            side_a = models.FloatField()
            side_b = models.FloatField()
            side_c = models.FloatField()
            type = models.TextField()

            def __str__(self):
                return (
                    f"{self.id}, "
                    f"{self.side_a}, "
                    f"{self.side_b}, "
                    f"{self.side_c}, "
                    f"{self.type}"
                )

        with connection.schema_editor() as editor:
            editor.create_model(Triangle)

        tables = connection.introspection.table_names(include_views=True)
        self.assertIn("backends_triangle", tables)

    def test_sql_delete_model(self):
        with connection.schema_editor() as editor:
            editor.delete_model(SimpleModel)

        tables = connection.introspection.table_names(include_views=True)
        self.assertNotIn("backends_simplemodel", tables)

    def test_sql_rename_table(self):
        old_table_name = OldNameModel._meta.db_table
        new_table_name = "backends_newnamemodel"

        with connection.schema_editor() as editor:
            editor.alter_db_table(
                OldNameModel,
                old_table_name,
                new_table_name
            )

        tables = connection.introspection.table_names(include_views=True)
        self.assertIn(new_table_name, tables)
        self.assertNotIn(old_table_name, tables)

        OldNameModel._meta.db_table = new_table_name
        self.assertEqual(OldNameModel._meta.db_table, new_table_name)

    def test_sql_create_column(self):
        table_columns_before = [f.name for f in MyModel._meta.get_fields()]
        self.assertNotIn("surname", table_columns_before)

        MyModel.objects.create(id=1, name="Anonymous1")
        new_field = TextField(max_length=15, blank=True, default="keks", null=True)
        new_field.set_attributes_from_name("surname")

        with connection.schema_editor() as editor:
            editor.add_field(MyModel, new_field)

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM `backends_mymodel`;")
            row = cursor.fetchall()

        self.assertTrue(len(row[0]) > 2)

    def test_sql_delete_column(self):
        field_to_remove = TextField(blank=True, default="shweps", null=True)
        field_to_remove.set_attributes_from_name("patronymic")

        with connection.schema_editor() as editor:
            editor.add_field(
                MyModel,
                field_to_remove
            )

        with connection.cursor() as cursor:
            self.assertTrue(
                len(connection.introspection.get_sequences(
                    cursor,
                    "backends_mymodel"
                )) > 3)

        with connection.schema_editor() as editor:
            editor.remove_field(
                MyModel,
                field_to_remove
            )

        with connection.cursor() as cursor:
            self.assertTrue(
                len(connection.introspection.get_sequences(
                    cursor, "backends_mymodel"
                )) > 2)

    def test_indexes_exists(self):
        index_true = _get_indexes()
        self.assertTrue(len(index_true) == 6)

    def test_sql_rename_index(self):
        old_index = Index(
            name="single_idx_w_name",
            fields=["single_idx_field_w_name"],
        )
        new_index = Index(
            name="single_idx_w_name_renamed",
            fields=["single_idx_field_w_name"],
        )

        index_true = _get_indexes()
        self.assertNotIn("single_idx_w_name_renamed", index_true)

        with connection.schema_editor() as editor:
            editor.rename_index(
                ModelWithIndexes,
                old_index,
                new_index
            )

        index_true = _get_indexes()
        self.assertIn("single_idx_w_name_renamed", index_true)

    def test_rename_index(self):
        index_true = _get_indexes()
        self.assertIn("partial_idx", index_true)
        self.assertNotIn("partial_idx_renamed", index_true)

        operation = migrations.RenameIndex(
            "backends_modelwithindexes",
            new_name="partial_idx_renamed",
            old_name="partial_idx"
        )
        self.assertEqual(
            operation.describe(),
            "Rename index partial_idx on "
            "backends_modelwithindexes to partial_idx_renamed",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "rename_partial_idx_partial_idx_renamed",
        )

    def test_sql_delete_index(self):
        index_true = _get_indexes()
        self.assertIn("composite_idx_w_name", index_true)

        index = Index(
            name="composite_idx_w_name",
            fields=[
                "first_part_composite_idx_field",
                "second_part_composite_idx_field",
                "third_part_composite_idx_field"
            ]
        )

        with connection.schema_editor() as editor:
            editor.remove_index(
                ModelWithIndexes,
                index
            )

        index_true = _get_indexes()
        self.assertNotIn("composite_idx_w_name", index_true)
