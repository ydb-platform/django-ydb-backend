"""
Exercise schema migrations through Django's migration executor (issue #41).

The schema tests in tests/backends/ydb/test_schema.py call schema-editor methods
directly. Real users instead run ``migrate``, which drives migrations through
:class:`~django.db.migrations.executor.MigrationExecutor`: it builds project
state from on-disk migrations, records applied migrations, and wraps each in the
schema editor. These tests run real migration files through that executor so the
end-to-end ``migrate`` path is covered, not just the schema editor.

Migration fixtures live in two packages, selected per test class with
``MIGRATION_MODULES``:

* ``migrations_supported`` - a linear chain of operations YDB supports.
* ``migrations_unsupported`` - a base table plus one branch per operation YDB
  cannot perform, so each can be targeted independently.
"""

import contextlib
from io import StringIO

from django.core.management import call_command
from django.db import NotSupportedError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase
from django.test import override_settings

APP = "migration_executor"

_SCHEMA_LOGGER = "django_ydb_backend.ydb_backend.backend.schema"

# Every table the fixtures can create, dropped defensively on teardown so a
# failing test cannot leave a table behind and break the next run's CreateModel.
_FIXTURE_TABLES = [
    "migration_executor_author",
    "migration_executor_author_renamed",
    "migration_executor_tag",
]


def _table_names():
    return set(connection.introspection.table_names())


def _columns(table):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
    return [column.name for column in description]


def _column_is_nullable(table, column):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
    return next(field.null_ok for field in description if field.name == column)


def _index_names(table):
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table)
    return [name for name, value in constraints.items() if value.get("index")]


class _ExecutorTestBase(TransactionTestCase):
    databases = {"default"}

    def _migrate(self, target):
        # A fresh executor reads the current applied state from the recorder,
        # so each call plans from where the previous one left off.
        MigrationExecutor(connection).migrate([(APP, target)])

    def tearDown(self):
        # Cleanup must not mask test failures, so swallow reversal errors and
        # fall back to dropping any fixture table left behind.
        with contextlib.suppress(Exception):
            self._migrate(None)
        existing = _table_names()
        for table in _FIXTURE_TABLES:
            if table in existing:
                with connection.schema_editor() as editor:
                    editor.execute(f"DROP TABLE {editor.quote_name(table)};")
        MigrationRecorder(connection).migration_qs.filter(app=APP).delete()


@override_settings(MIGRATION_MODULES={APP: "migration_executor.migrations_supported"})
class SupportedMigrationsExecutorTests(_ExecutorTestBase):
    """Operations YDB supports must apply through the executor and reverse."""

    def test_create_model(self):
        self._migrate("0001_initial")

        tables = _table_names()
        self.assertIn("migration_executor_author", tables)
        self.assertIn("migration_executor_tag", tables)

    def test_migration_is_recorded(self):
        self._migrate("0001_initial")

        applied = MigrationRecorder(connection).applied_migrations()
        self.assertIn((APP, "0001_initial"), applied)

    def test_add_nullable_column(self):
        self._migrate("0002_columns_and_index")

        self.assertIn("bio", _columns("migration_executor_author"))
        self.assertTrue(_column_is_nullable("migration_executor_author", "bio"))

    def test_add_not_null_column_with_default(self):
        self._migrate("0002_columns_and_index")

        self.assertIn("score", _columns("migration_executor_author"))
        self.assertFalse(_column_is_nullable("migration_executor_author", "score"))
        # The default is materialised into the DDL, so a row inserted without
        # the column is backfilled instead of rejected.
        with connection.cursor() as cursor:
            cursor.execute(
                "UPSERT INTO `migration_executor_author` (id, name) VALUES (1, 'a');"
            )
            cursor.execute(
                "SELECT score FROM `migration_executor_author` WHERE id = 1;"
            )
            self.assertEqual(cursor.fetchall()[0][0], 0)

    def test_add_index(self):
        self._migrate("0002_columns_and_index")

        self.assertIn("me_author_name_idx", _index_names("migration_executor_author"))

    def test_drop_index_and_column(self):
        self._migrate("0002_columns_and_index")
        self._migrate("0003_drops")

        self.assertNotIn(
            "me_author_name_idx", _index_names("migration_executor_author")
        )
        self.assertNotIn("bio", _columns("migration_executor_author"))

    def test_rename_table_and_delete_model(self):
        self._migrate("0004_rename_and_delete")

        tables = _table_names()
        self.assertIn("migration_executor_author_renamed", tables)
        self.assertNotIn("migration_executor_author", tables)
        self.assertNotIn("migration_executor_tag", tables)

    def test_full_chain_reverses_cleanly(self):
        self._migrate("0004_rename_and_delete")
        self._migrate(None)

        tables = _table_names()
        for table in _FIXTURE_TABLES:
            self.assertNotIn(table, tables)
        self.assertNotIn(
            (APP, "0001_initial"),
            MigrationRecorder(connection).applied_migrations(),
        )

    def test_sqlmigrate_emits_create_table_and_default(self):
        initial_sql = StringIO()
        call_command("sqlmigrate", APP, "0001", stdout=initial_sql)
        self.assertIn("CREATE TABLE", initial_sql.getvalue().upper())

        columns_sql = StringIO()
        call_command("sqlmigrate", APP, "0002", stdout=columns_sql)
        rendered = columns_sql.getvalue()
        self.assertIn("ADD COLUMN", rendered.upper())
        # The NOT NULL column carries its default literal.
        self.assertIn("DEFAULT 0", rendered)


@override_settings(MIGRATION_MODULES={APP: "migration_executor.migrations_unsupported"})
class UnsupportedMigrationsExecutorTests(_ExecutorTestBase):
    """Operations YDB cannot perform must fail predictably through the
    executor: schema-corrupting changes raise, unenforceable ones warn."""

    def _assert_raises(self, target):
        self._migrate("0001_initial")
        with self.assertRaises(NotSupportedError):
            self._migrate(target)

    def _assert_warns(self, target):
        self._migrate("0001_initial")
        with self.assertLogs(_SCHEMA_LOGGER, level="WARNING"):
            self._migrate(target)

    def test_rename_column_raises(self):
        self._assert_raises("0002_rename_column")

    def test_alter_type_raises(self):
        self._assert_raises("0002_alter_type")

    def test_alter_primary_key_raises(self):
        self._assert_raises("0002_alter_pk")

    def test_make_not_null_warns(self):
        self._assert_warns("0002_make_not_null")

    def test_add_unique_constraint_warns(self):
        self._assert_warns("0002_unique_constraint")

    def test_alter_default_is_noop(self):
        self._migrate("0001_initial")
        # Defaults are not stored in YDB, so a default change applies cleanly
        # without warning and is recorded as applied.
        with self.assertNoLogs(_SCHEMA_LOGGER, level="WARNING"):
            self._migrate("0002_alter_default")
        self.assertIn(
            (APP, "0002_alter_default"),
            MigrationRecorder(connection).applied_migrations(),
        )
