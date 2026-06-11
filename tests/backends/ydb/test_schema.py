from django.db import connection
from django.db import models
from django.db.models import CASCADE
from django.db.models import ForeignKey
from django.db.models import Index
from django.db.models import IntegerField
from django.db.models import TextField
from django.test import TransactionTestCase

from ..models import DbColumnModel
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


def _get_columns(table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor, table_name
        )
    return [column.name for column in description]


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

    def test_create_model_with_db_column(self):
        columns = _get_columns("backends_dbcolumnmodel")
        self.assertIn("custom_full_name", columns)
        self.assertIn("custom_age", columns)
        # The Django field names must not leak into the database schema.
        self.assertNotIn("full_name", columns)
        self.assertNotIn("age", columns)

    def test_query_with_db_column(self):
        DbColumnModel.objects.create(id=1, full_name="Ivan Petrov", age=30)

        fetched = DbColumnModel.objects.get(full_name="Ivan Petrov")
        self.assertEqual(fetched.id, 1)
        self.assertEqual(fetched.full_name, "Ivan Petrov")
        self.assertEqual(fetched.age, 30)

        # Filtering on the db_column-backed field must reach the right column.
        self.assertTrue(DbColumnModel.objects.filter(age=30).exists())

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT custom_full_name, custom_age "
                "FROM `backends_dbcolumnmodel` WHERE id = 1;"
            )
            row = cursor.fetchall()
        self.assertEqual(row[0][0], "Ivan Petrov")
        self.assertEqual(row[0][1], 30)

    def test_add_field_with_db_column(self):
        new_field = TextField(null=True, db_column="custom_surname")
        new_field.set_attributes_from_name("surname")

        with connection.schema_editor() as editor:
            editor.add_field(MyModel, new_field)

        columns = _get_columns("backends_mymodel")
        self.assertIn("custom_surname", columns)
        self.assertNotIn("surname", columns)

    def test_remove_field_with_db_column(self):
        new_field = IntegerField(null=True, db_column="custom_rank")
        new_field.set_attributes_from_name("rank")

        with connection.schema_editor() as editor:
            editor.add_field(MyModel, new_field)
        self.assertIn("custom_rank", _get_columns("backends_mymodel"))

        with connection.schema_editor() as editor:
            editor.remove_field(MyModel, new_field)
        self.assertNotIn("custom_rank", _get_columns("backends_mymodel"))

    def test_add_field_keeps_relation_scalar_column_name(self):
        fk_field = ForeignKey(SimpleModel, on_delete=CASCADE, null=True)
        fk_field.set_attributes_from_name("simple")

        with connection.schema_editor() as editor:
            editor.add_field(MyModel, fk_field)

        columns = _get_columns("backends_mymodel")
        # Relation columns keep the "_id" scalar suffix (field.column),
        # not the bare field name.
        self.assertIn("simple_id", columns)
        self.assertNotIn("simple", columns)

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
        self.assertIn("single_idx_w_name", index_true)
        self.assertNotIn("single_idx_w_name_renamed", index_true)

        with connection.schema_editor() as editor:
            editor.rename_index(
                ModelWithIndexes,
                old_index,
                new_index
            )

        index_true = _get_indexes()
        self.assertIn("single_idx_w_name_renamed", index_true)
        self.assertNotIn("single_idx_w_name", index_true)

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
