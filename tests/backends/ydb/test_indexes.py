from django.db import connection
from django.db import models
from django.db.models import Index
from django.test import SimpleTestCase
from django.test import TransactionTestCase


class IndexTestBook(models.Model):
    """Dedicated model for index tests. Table lifecycle managed by setUp/tearDown."""

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=256)
    author = models.CharField(max_length=256)
    year = models.IntegerField(null=True)

    class Meta:
        app_label = "backends"
        db_table = "ydb_idx_test_book"
        managed = False

    def __str__(self):
        return f"{self.id}: {self.title}"


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


class TestIndexFeatureFlags(SimpleTestCase):
    def test_covering_indexes_supported(self):
        self.assertTrue(connection.features.supports_covering_indexes)

    def test_expression_indexes_not_supported(self):
        self.assertFalse(connection.features.supports_expression_indexes)

    def test_partial_indexes_not_supported(self):
        self.assertFalse(connection.features.supports_partial_indexes)

    def test_rename_index_supported(self):
        self.assertTrue(connection.features.can_rename_index)

    def test_unique_index_sql_disabled(self):
        # YDB ALTER TABLE ADD INDEX has no UNIQUE variant.
        self.assertIsNone(connection.SchemaEditorClass.sql_create_unique_index)


# ---------------------------------------------------------------------------
# SQL generation tests (collect_sql=True — no live DB required)
# ---------------------------------------------------------------------------

_TABLE = "`ydb_idx_test_book`"


class TestIndexSQLGeneration(SimpleTestCase):
    def _sql(self, fn):
        with connection.schema_editor(collect_sql=True) as editor:
            fn(editor)
        self.assertEqual(len(editor.collected_sql), 1)
        return editor.collected_sql[0]

    # --- CREATE INDEX ---

    def test_regular_index(self):
        idx = Index(fields=["title"], name="t_title_idx")
        self.assertEqual(
            self._sql(lambda ed: ed.add_index(IndexTestBook, idx)),
            f"ALTER TABLE {_TABLE} ADD INDEX `t_title_idx` GLOBAL ON (`title`);",
        )

    def test_composite_index(self):
        idx = Index(fields=["author", "year"], name="t_comp_idx")
        self.assertEqual(
            self._sql(lambda ed: ed.add_index(IndexTestBook, idx)),
            f"ALTER TABLE {_TABLE} ADD INDEX `t_comp_idx`"
            f" GLOBAL ON (`author`, `year`);",
        )

    def test_covering_index_single_cover_column(self):
        idx = Index(fields=["title"], include=["author"], name="t_cover_idx")
        self.assertEqual(
            self._sql(lambda ed: ed.add_index(IndexTestBook, idx)),
            f"ALTER TABLE {_TABLE} ADD INDEX `t_cover_idx`"
            f" GLOBAL ON (`title`) COVER (`author`);",
        )

    def test_covering_index_multiple_cover_columns(self):
        idx = Index(
            fields=["title"], include=["author", "year"], name="t_cover2_idx"
        )
        self.assertEqual(
            self._sql(lambda ed: ed.add_index(IndexTestBook, idx)),
            f"ALTER TABLE {_TABLE} ADD INDEX `t_cover2_idx`"
            f" GLOBAL ON (`title`) COVER (`author`, `year`);",
        )

    # --- RENAME INDEX ---

    def test_rename_index(self):
        old = Index(fields=["title"], name="t_old_idx")
        new = Index(fields=["title"], name="t_new_idx")
        self.assertEqual(
            self._sql(lambda ed: ed.rename_index(IndexTestBook, old, new)),
            f"ALTER TABLE {_TABLE} RENAME INDEX `t_old_idx` TO `t_new_idx`;",
        )

    # --- DROP INDEX ---

    def test_delete_index(self):
        idx = Index(fields=["title"], name="t_drop_idx")
        self.assertEqual(
            self._sql(lambda ed: ed.remove_index(IndexTestBook, idx)),
            f"ALTER TABLE {_TABLE} DROP INDEX `t_drop_idx`;",
        )


# ---------------------------------------------------------------------------
# Integration tests (require live YDB)
# ---------------------------------------------------------------------------


class TestIndexIntegration(TransactionTestCase):
    databases = {"default"}

    # -- table lifecycle --

    def setUp(self):
        self._ensure_clean_table()

    def tearDown(self):
        self._drop_table()
        super().tearDown()

    def _ensure_clean_table(self):
        try:
            with connection.schema_editor() as editor:
                editor.delete_model(IndexTestBook)
        except Exception:  # noqa: BLE001
            pass
        with connection.schema_editor() as editor:
            editor.create_model(IndexTestBook)

    def _drop_table(self):
        try:
            with connection.schema_editor() as editor:
                editor.delete_model(IndexTestBook)
        except Exception:  # noqa: BLE001
            pass

    # -- helpers --

    def _add_index(self, index):
        with connection.schema_editor() as editor:
            editor.add_index(IndexTestBook, index)

    def _remove_index(self, index):
        with connection.schema_editor() as editor:
            editor.remove_index(IndexTestBook, index)

    def _get_indexes(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, IndexTestBook._meta.db_table
            )
        return {k: v for k, v in constraints.items() if v.get("index")}

    def _insert(self, **kwargs):
        IndexTestBook.objects.create(**kwargs)

    def _select_view(self, index_name, where_col, where_val, select_cols="*"):
        table = IndexTestBook._meta.db_table
        sql = (
            f"SELECT {select_cols} FROM `{table}` VIEW `{index_name}`"
            f" WHERE `{where_col}` = '{where_val}';"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    # -- CREATE INDEX --

    def test_create_regular_index_appears_in_introspection(self):
        idx = Index(fields=["title"], name="i_title_idx")
        self._add_index(idx)
        self.assertIn("i_title_idx", self._get_indexes())

    def test_create_composite_index_appears_in_introspection(self):
        idx = Index(fields=["author", "year"], name="i_comp_idx")
        self._add_index(idx)
        self.assertIn("i_comp_idx", self._get_indexes())

    def test_create_covering_index_appears_in_introspection(self):
        idx = Index(fields=["title"], include=["author"], name="i_cover_idx")
        self._add_index(idx)
        self.assertIn("i_cover_idx", self._get_indexes())

    def test_create_multiple_indexes_all_appear(self):
        self._add_index(Index(fields=["title"], name="i_multi_title"))
        self._add_index(Index(fields=["author"], name="i_multi_author"))
        indexes = self._get_indexes()
        self.assertIn("i_multi_title", indexes)
        self.assertIn("i_multi_author", indexes)

    # -- DELETE INDEX --

    def test_delete_index_removes_from_introspection(self):
        idx = Index(fields=["title"], name="i_del_idx")
        self._add_index(idx)
        self.assertIn("i_del_idx", self._get_indexes())
        self._remove_index(idx)
        self.assertNotIn("i_del_idx", self._get_indexes())

    def test_delete_one_index_leaves_others(self):
        idx1 = Index(fields=["title"], name="i_keep_idx")
        idx2 = Index(fields=["author"], name="i_gone_idx")
        self._add_index(idx1)
        self._add_index(idx2)
        self._remove_index(idx2)
        indexes = self._get_indexes()
        self.assertIn("i_keep_idx", indexes)
        self.assertNotIn("i_gone_idx", indexes)

    # -- RENAME INDEX --

    def test_rename_index_old_name_gone_new_name_present(self):
        old = Index(fields=["title"], name="i_rn_old")
        new = Index(fields=["title"], name="i_rn_new")
        self._add_index(old)
        with connection.schema_editor() as editor:
            editor.rename_index(IndexTestBook, old, new)
        indexes = self._get_indexes()
        self.assertNotIn("i_rn_old", indexes)
        self.assertIn("i_rn_new", indexes)

    # -- SELECT VIEW (index hint) --

    def test_regular_index_select_view_returns_correct_rows(self):
        idx = Index(fields=["title"], name="i_view_idx")
        self._add_index(idx)
        self._insert(id=1, title="Gomu Gomu no Mi", author="Luffy", year=1997)
        self._insert(id=2, title="Thousand Sunny", author="Franky", year=2005)

        rows = self._select_view("i_view_idx", "title", "Gomu Gomu no Mi", "`title`")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Gomu Gomu no Mi")

    def test_regular_index_select_view_empty_for_missing_value(self):
        idx = Index(fields=["title"], name="i_empty_idx")
        self._add_index(idx)
        self._insert(id=1, title="One Piece", author="Nami", year=1997)

        rows = self._select_view("i_empty_idx", "title", "Poseidon", "`title`")
        self.assertEqual(rows, [])

    def test_covering_index_select_view_returns_cover_columns(self):
        idx = Index(fields=["title"], include=["author"], name="i_cov_view_idx")
        self._add_index(idx)
        self._insert(id=1, title="All Blue", author="Sanji", year=1997)

        rows = self._select_view(
            "i_cov_view_idx", "title", "All Blue", "`title`, `author`"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "All Blue")
        self.assertEqual(rows[0][1], "Sanji")

    def test_covering_index_select_view_multiple_cover_columns(self):
        idx = Index(
            fields=["title"], include=["author", "year"], name="i_cov2_view_idx"
        )
        self._add_index(idx)
        self._insert(id=1, title="Will of D", author="Robin", year=1997)

        rows = self._select_view(
            "i_cov2_view_idx",
            "title",
            "Will of D",
            "`title`, `author`, `year`",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Robin")
        self.assertEqual(rows[0][2], 1997)

    def test_composite_index_select_view_by_first_column(self):
        idx = Index(fields=["author", "year"], name="i_comp_view_idx")
        self._add_index(idx)
        self._insert(id=1, title="Straw Hat Pirates", author="Ace", year=1997)
        self._insert(id=2, title="Whitebeard Pirates", author="Sabo", year=1997)

        rows = self._select_view(
            "i_comp_view_idx", "author", "Ace", "`author`"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Ace")
