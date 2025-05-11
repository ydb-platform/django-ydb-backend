from django.db import connection
from django.db import models
from django.db.models import TextField
from django.test import SimpleTestCase

from ..models import MyModel
from ..models import OldNameModel
from ..models import SimpleModel


class TestDatabaseSchema(SimpleTestCase):
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


    # def test_transaction_rollback(self):
    #     try:
    #         with transaction.atomic():
    #             self.schema.sql_create_table(
    #                   self.test_table_name,
    #                   {"id": "serial primary key"}
    #             )
    #             raise Exception("Test error")
    #     except:
    #         pass
    #
    #     with connection.cursor() as cursor:
    #         cursor.execute(f"SELECT to_regclass('{self.test_table_name}');")
    #         result = cursor.fetchone()[0]
    #     self.assertIsNone(result)
    #
    # def test_composite_primary_key(self):
    #     self.schema.sql_create_table(self.test_table_name, {
    #         "id1": "integer",
    #         "id2": "integer",
    #         "PRIMARY KEY": "(id1, id2)"
    #     })
    #
    #     with connection.cursor() as cursor:
    #         cursor.execute(f"""
    #             SELECT constraint_name
    #             FROM information_schema.table_constraints
    #             WHERE table_name='{self.test_table_name}'
    #             AND constraint_type='PRIMARY KEY';
    #         """)
    #         result = cursor.fetchone()
    #     self.assertIsNotNone(result)

    # def test_sql_delete_index(self):
    #     pass
    #
    # def test_sql_rename_index(self):
    #     pass
    #
    # def test_sql_create_index(self):
    #     pass
    #
    # def test_sql_create_unique_index(self):
    #     pass
    #
    # def test_sql_update_with_default(self):
    #     pass
