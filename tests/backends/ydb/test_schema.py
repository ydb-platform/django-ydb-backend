from datetime import date
from datetime import time
from enum import Enum
from uuid import UUID

import django
from django.db import NotSupportedError
from django.db import connection
from django.db import models
from django.db.models import CASCADE
from django.db.models import CheckConstraint
from django.db.models import ForeignKey
from django.db.models import Index
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import TextField
from django.db.models import UniqueConstraint
from django.test import SimpleTestCase
from django.test import TransactionTestCase
from ydb_backend.backend.schema import _default_literal
from ydb_backend.backend.schema import _quote_value

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


def _column_is_nullable(table_name, column):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor, table_name
        )
    return next(field.null_ok for field in description if field.name == column)


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

        self.assertIn("patronymic", _get_columns("backends_mymodel"))

        with connection.schema_editor() as editor:
            editor.remove_field(
                MyModel,
                field_to_remove
            )

        self.assertNotIn("patronymic", _get_columns("backends_mymodel"))

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


def _named_field(field_class, name, **kwargs):
    field = field_class(**kwargs)
    field.set_attributes_from_name(name)
    return field


_SCHEMA_LOGGER = "django_ydb_backend.ydb_backend.backend.schema"


class TestUnsupportedSchemaOperations(TransactionTestCase):
    """
    Schema alterations YDB cannot perform must not silently pass (issue #35):
    schema-corrupting changes (rename/type/PK change) fail loudly, while
    unenforceable ones (constraints, uniqueness, making a column NOT NULL) are
    skipped with a warning so ``migrate`` of stock Django apps keeps working.
    Relaxing NOT NULL to nullable is actually applied.
    """

    databases = {"default"}

    def _assert_raises(self, method_name, *args):
        editor = connection.schema_editor()
        with self.assertRaises(NotSupportedError):
            getattr(editor, method_name)(*args)

    def _assert_warns(self, method_name, *args):
        editor = connection.schema_editor()
        with self.assertLogs(_SCHEMA_LOGGER, level="WARNING"):
            getattr(editor, method_name)(*args)

    def test_add_unique_constraint_warns(self):
        constraint = UniqueConstraint(fields=["name"], name="uq_mymodel_name")
        self._assert_warns("add_constraint", MyModel, constraint)

    def test_add_check_constraint_warns(self):
        # CheckConstraint.check was renamed to .condition in Django 5.1 and
        # removed in 6.0.
        if django.VERSION >= (5, 1):
            constraint = CheckConstraint(condition=Q(id__gte=0), name="ck_mymodel")
        else:
            constraint = CheckConstraint(check=Q(id__gte=0), name="ck_mymodel")
        self._assert_warns("add_constraint", MyModel, constraint)

    def test_remove_constraint_is_noop(self):
        constraint = UniqueConstraint(fields=["name"], name="uq_mymodel_name")
        # Nothing was ever created, so dropping it must not raise.
        connection.schema_editor().remove_constraint(MyModel, constraint)

    def test_alter_field_type_change_raises(self):
        old_field = _named_field(IntegerField, "name")
        new_field = _named_field(TextField, "name")
        self._assert_raises("alter_field", MyModel, old_field, new_field)

    def test_alter_field_rename_raises(self):
        old_field = _named_field(IntegerField, "old_name")
        new_field = _named_field(IntegerField, "new_name")
        self._assert_raises("alter_field", MyModel, old_field, new_field)

    def test_alter_field_primary_key_change_raises(self):
        old_field = _named_field(IntegerField, "name")
        new_field = _named_field(IntegerField, "name", primary_key=True)
        self._assert_raises("alter_field", MyModel, old_field, new_field)

    def test_alter_field_make_nullable_applies(self):
        # NOT NULL -> nullable is supported via ALTER COLUMN ... DROP NOT NULL.
        not_null = _named_field(models.CharField, "name", max_length=100)
        nullable = _named_field(models.CharField, "name", max_length=100, null=True)
        with connection.schema_editor() as editor:
            editor.alter_field(MyModel, not_null, nullable)
        self.assertTrue(_column_is_nullable("backends_mymodel", "name"))

    def test_alter_field_make_not_null_warns(self):
        # nullable -> NOT NULL cannot be enforced after creation.
        nullable = _named_field(IntegerField, "name", null=True)
        not_null = _named_field(IntegerField, "name", null=False)
        self._assert_warns("alter_field", MyModel, nullable, not_null)

    def test_alter_field_add_unique_warns(self):
        old_field = _named_field(IntegerField, "name")
        new_field = _named_field(IntegerField, "name", unique=True)
        self._assert_warns("alter_field", MyModel, old_field, new_field)

    def test_alter_field_default_change_is_noop(self):
        # Defaults are not stored in YDB, so changing one is a harmless no-op.
        old_field = _named_field(IntegerField, "name", default=1)
        new_field = _named_field(IntegerField, "name", default=2)
        connection.schema_editor().alter_field(MyModel, old_field, new_field)

    def test_alter_unique_together_add_warns(self):
        self._assert_warns(
            "alter_unique_together", MyModel, [], [("id", "name")]
        )

    def test_alter_unique_together_clear_is_noop(self):
        connection.schema_editor().alter_unique_together(
            MyModel, [("id", "name")], []
        )

    def test_alter_field_db_index_add_and_drop(self):
        def index_columns():
            with connection.cursor() as cursor:
                constraints = connection.introspection.get_constraints(
                    cursor, "backends_mymodel"
                )
            return [
                value["columns"]
                for value in constraints.values()
                if value["index"] and not value["primary_key"]
            ]

        no_index = _named_field(TextField, "name")
        indexed = _named_field(TextField, "name", db_index=True)

        with connection.schema_editor() as editor:
            editor.alter_field(MyModel, no_index, indexed)
        self.assertIn(["name"], index_columns())

        with connection.schema_editor() as editor:
            editor.alter_field(MyModel, indexed, no_index)
        self.assertNotIn(["name"], index_columns())


class _Color(Enum):
    NUMBER = 1
    LABEL = "red"


class QuoteValueTests(SimpleTestCase):
    """Pure literal-quoting helpers used by the schema editor (no database)."""

    def test_quote_value_by_type(self):
        cases = [
            (None, "NULL"),
            (5, "'5'"),
            (1.5, "'1.5'"),
            (date(2020, 1, 2), "'2020-01-02'"),
            (time(10, 20, 30), "'10:20:30'"),
            ("a'b", "'a''b'"),
            ([1, "x"], "['1', 'x']"),
            (
                UUID("12345678-1234-5678-1234-567812345678"),
                "'12345678-1234-5678-1234-567812345678'",
            ),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_quote_value(value), expected)

    def test_quote_value_enum_uses_member_value(self):
        self.assertEqual(_quote_value(_Color.NUMBER), "'1'")
        self.assertEqual(_quote_value(_Color.LABEL), "'red'")

    def test_quote_value_unsupported_type_raises(self):
        with self.assertRaisesMessage(ValueError, "Unsupported type"):
            _quote_value(object())


class DefaultLiteralTests(SimpleTestCase):
    """Column-default literal rendering (numbers and booleans unquoted)."""

    def test_default_literal(self):
        self.assertEqual(_default_literal(True), "true")
        self.assertEqual(_default_literal(False), "false")
        self.assertEqual(_default_literal(7), "7")
        self.assertEqual(_default_literal(1.5), "1.5")
        self.assertEqual(_default_literal(_Color.NUMBER), "1")
        self.assertEqual(_default_literal("a'b"), "'a''b'")

    def test_default_literal_unsupported_type_raises(self):
        with self.assertRaisesMessage(NotSupportedError, "column default"):
            _default_literal([1, 2])
