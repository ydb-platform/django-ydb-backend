"""
Tests for DatabaseFeatures: flag values and behavioral verification.

Flag assertions document what YDB supports. Integration tests verify that
the flags accurately reflect live database behavior.
"""
from django.db import connection
from django.db import models
from django.db.models import Sum
from django.db.models import Window
from django.db.models.expressions import RowRange
from django.db.models.expressions import ValueRange
from django.db.utils import NotSupportedError
from django.test import SimpleTestCase
from django.test import TransactionTestCase

# ---------------------------------------------------------------------------
# Flag value assertions (no live DB required)
# ---------------------------------------------------------------------------


class TestFeatureFlags(SimpleTestCase):
    """Every explicit DatabaseFeatures override is asserted here."""

    # --- GROUP BY ---
    def test_allows_group_by_selected_pks(self):
        self.assertTrue(connection.features.allows_group_by_selected_pks)

    def test_no_group_by_select_index(self):
        # YDB rejects "GROUP BY 1" ordinal references.
        self.assertFalse(connection.features.allows_group_by_select_index)

    # --- UPDATE / DELETE self-reference ---
    def test_no_update_self_select(self):
        self.assertFalse(connection.features.update_can_self_select)

    def test_no_delete_self_reference_subquery(self):
        self.assertFalse(connection.features.delete_can_self_reference_subquery)

    # --- NULL / string semantics ---
    def test_does_not_interpret_empty_strings_as_nulls(self):
        self.assertFalse(connection.features.interprets_empty_strings_as_nulls)

    def test_ignores_table_name_case(self):
        self.assertTrue(connection.features.ignores_table_name_case)

    # --- Unique / nullable constraints ---
    def test_no_nullable_unique_constraints(self):
        self.assertFalse(connection.features.supports_nullable_unique_constraints)

    def test_no_partially_nullable_unique_constraints(self):
        self.assertFalse(
            connection.features.supports_partially_nullable_unique_constraints
        )

    # --- Bulk insert ---
    def test_no_bulk_insert_return_rows(self):
        self.assertFalse(connection.features.can_return_rows_from_bulk_insert)

    # --- Transactions / savepoints ---
    def test_transactions_supported(self):
        self.assertTrue(connection.features.supports_transactions)

    def test_no_savepoints(self):
        self.assertFalse(connection.features.uses_savepoints)

    # --- References ---
    def test_no_forward_references(self):
        self.assertFalse(connection.features.supports_forward_references)

    # --- Native types ---
    def test_native_uuid_field(self):
        self.assertTrue(connection.features.has_native_uuid_field)

    def test_native_duration_field(self):
        self.assertTrue(connection.features.has_native_duration_field)

    def test_temporal_subtraction_supported(self):
        self.assertTrue(connection.features.supports_temporal_subtraction)

    # --- Regex ---
    def test_no_regex_backreferencing(self):
        self.assertFalse(connection.features.supports_regex_backreferencing)

    # --- Timezone data ---
    def test_no_zoneinfo_database(self):
        self.assertFalse(connection.features.has_zoneinfo_database)

    # --- ORDER BY ---
    def test_no_order_by_nulls_modifier(self):
        self.assertFalse(connection.features.supports_order_by_nulls_modifier)

    # --- Auto PK ---
    def test_no_auto_pk_0(self):
        self.assertFalse(connection.features.allows_auto_pk_0)

    def test_no_sequence_reset(self):
        self.assertFalse(connection.features.supports_sequence_reset)

    # --- Introspection ---
    def test_no_introspect_default(self):
        self.assertFalse(connection.features.can_introspect_default)

    def test_no_introspect_foreign_keys(self):
        self.assertFalse(connection.features.can_introspect_foreign_keys)

    def test_no_introspect_check_constraints(self):
        self.assertFalse(connection.features.can_introspect_check_constraints)

    def test_no_introspect_json_field(self):
        self.assertFalse(connection.features.can_introspect_json_field)

    # --- Schema / DDL ---
    def test_schema_editor_clientside_param_binding(self):
        self.assertTrue(connection.features.schema_editor_uses_clientside_param_binding)

    def test_no_foreign_keys(self):
        self.assertFalse(connection.features.supports_foreign_keys)

    def test_no_inline_fk(self):
        self.assertFalse(connection.features.can_create_inline_fk)

    def test_no_auto_index_foreign_keys(self):
        self.assertFalse(connection.features.indexes_foreign_keys)

    def test_no_column_check_constraints(self):
        self.assertFalse(connection.features.supports_column_check_constraints)

    def test_no_table_check_constraints(self):
        self.assertFalse(connection.features.supports_table_check_constraints)

    def test_no_expression_defaults(self):
        self.assertFalse(connection.features.supports_expression_defaults)

    def test_no_default_keyword_in_insert(self):
        self.assertFalse(connection.features.supports_default_keyword_in_insert)

    def test_no_default_keyword_in_bulk_insert(self):
        self.assertFalse(connection.features.supports_default_keyword_in_bulk_insert)

    # --- SELECT FOR UPDATE ---
    def test_no_select_for_update_with_limit(self):
        self.assertFalse(connection.features.supports_select_for_update_with_limit)

    # --- Compound queries ---
    def test_no_select_intersection(self):
        self.assertFalse(connection.features.supports_select_intersection)

    def test_no_select_difference(self):
        self.assertFalse(connection.features.supports_select_difference)

    def test_no_parentheses_in_compound(self):
        self.assertFalse(connection.features.supports_parentheses_in_compound)

    # --- Window functions ---
    def test_over_clause_supported(self):
        self.assertTrue(connection.features.supports_over_clause)

    def test_only_unbounded_range_frames(self):
        # YDB RANGE frames only work with UNBOUNDED PRECEDING/FOLLOWING.
        # Bounded RANGE (e.g. RANGE BETWEEN 1 PRECEDING AND CURRENT ROW) fails.
        self.assertTrue(
            connection.features.only_supports_unbounded_with_preceding_and_following
        )

    # --- Conflicts ---
    def test_no_ignore_conflicts(self):
        self.assertFalse(connection.features.supports_ignore_conflicts)

    # --- Indexes ---
    def test_no_partial_indexes(self):
        self.assertFalse(connection.features.supports_partial_indexes)

    def test_no_functions_in_partial_indexes(self):
        self.assertFalse(connection.features.supports_functions_in_partial_indexes)

    def test_covering_indexes_supported(self):
        self.assertTrue(connection.features.supports_covering_indexes)

    def test_no_expression_indexes(self):
        self.assertFalse(connection.features.supports_expression_indexes)

    def test_no_multiple_constraints_same_fields(self):
        self.assertFalse(connection.features.allows_multiple_constraints_on_same_fields)

    # --- JSON ---
    def test_native_json_field(self):
        self.assertTrue(connection.features.has_native_json_field)

    def test_json_key_contains_list_matching_requires_list(self):
        self.assertTrue(
            connection.features.json_key_contains_list_matching_requires_list
        )

    def test_no_json_object_function(self):
        self.assertFalse(connection.features.has_json_object_function)

    # --- Collation ---
    def test_no_collation_on_charfield(self):
        self.assertFalse(connection.features.supports_collation_on_charfield)

    def test_no_collation_on_textfield(self):
        self.assertFalse(connection.features.supports_collation_on_textfield)

    def test_no_non_deterministic_collations(self):
        self.assertFalse(connection.features.supports_non_deterministic_collations)

    # --- Bounded RANGE frame raises NotSupportedError at Django level ---
    def test_bounded_range_frame_raises_not_supported(self):
        with self.assertRaises(NotSupportedError):
            connection.ops.window_frame_range_start_end(start=-1, end=0)

    def test_bounded_range_following_raises_not_supported(self):
        with self.assertRaises(NotSupportedError):
            connection.ops.window_frame_range_start_end(start=None, end=1)

    def test_unbounded_range_frame_is_allowed(self):
        start, end = connection.ops.window_frame_range_start_end(start=None, end=0)
        self.assertEqual(start, "UNBOUNDED PRECEDING")
        self.assertEqual(end, "CURRENT ROW")

    def test_bounded_rows_frame_is_allowed(self):
        # ROWS frames are fine with bounded offsets.
        start, end = connection.ops.window_frame_rows_start_end(start=-1, end=0)
        self.assertEqual(start, "1 PRECEDING")
        self.assertEqual(end, "CURRENT ROW")


# ---------------------------------------------------------------------------
# Window function ORM integration tests
# ---------------------------------------------------------------------------


class WindowTestModel(models.Model):
    id = models.IntegerField(primary_key=True)
    bounty = models.IntegerField()

    class Meta:
        app_label = "backends"
        db_table = "ydb_feat_window"
        managed = False

    def __str__(self):
        return str(self.id)


class TestWindowFunctions(TransactionTestCase):
    databases = {"default"}

    def setUp(self):
        try:
            with connection.schema_editor() as ed:
                ed.delete_model(WindowTestModel)
        except Exception:  # noqa: BLE001
            pass
        with connection.schema_editor() as ed:
            ed.create_model(WindowTestModel)

    def tearDown(self):
        try:
            with connection.schema_editor() as ed:
                ed.delete_model(WindowTestModel)
        except Exception:  # noqa: BLE001
            pass
        super().tearDown()

    def _insert(self, pk, bounty):
        WindowTestModel.objects.create(id=pk, bounty=bounty)

    def test_unbounded_rows_frame_cumulative_sum(self):
        # Default: no explicit frame → OVER (ORDER BY id).
        self._insert(pk=1, bounty=30_000_000)   # Luffy
        self._insert(pk=2, bounty=320_000_000)  # Zoro
        self._insert(pk=3, bounty=66_000_000)   # Nami

        table = WindowTestModel._meta.db_table
        qs = (
            WindowTestModel.objects
            .annotate(running=Window(Sum("bounty"), order_by="id"))
            .values_list("id", "running")
            .order_by("id")
        )
        self.assertEqual(
            str(qs.query),
            f"SELECT `{table}`.`id` AS `id`, SUM(`{table}`.`bounty`) OVER"
            f" (ORDER BY `{table}`.`id`) AS `running`"
            f" FROM `{table}` ORDER BY `{table}`.`id` ASC",
        )

        rows = list(qs)
        self.assertEqual(rows[0][1], 30_000_000)
        self.assertEqual(rows[1][1], 350_000_000)
        self.assertEqual(rows[2][1], 416_000_000)

    def test_bounded_rows_preceding_frame(self):
        # RowRange(start=-1, end=0) → ROWS BETWEEN 1 PRECEDING AND CURRENT ROW.
        self._insert(pk=1, bounty=30_000_000)   # Luffy
        self._insert(pk=2, bounty=320_000_000)  # Zoro
        self._insert(pk=3, bounty=66_000_000)   # Nami

        table = WindowTestModel._meta.db_table
        qs = (
            WindowTestModel.objects
            .annotate(
                sliding=Window(
                    Sum("bounty"),
                    order_by="id",
                    frame=RowRange(start=-1, end=0),
                )
            )
            .values_list("id", "sliding")
            .order_by("id")
        )
        self.assertEqual(
            str(qs.query),
            f"SELECT `{table}`.`id` AS `id`, SUM(`{table}`.`bounty`) OVER"
            f" (ORDER BY `{table}`.`id` ROWS BETWEEN 1 PRECEDING AND CURRENT ROW)"
            f" AS `sliding` FROM `{table}` ORDER BY `{table}`.`id` ASC",
        )

        rows = list(qs)
        self.assertEqual(rows[0][1], 30_000_000)            # only Luffy
        self.assertEqual(rows[1][1], 350_000_000)           # Luffy + Zoro
        self.assertEqual(rows[2][1], 386_000_000)           # Zoro + Nami

    def test_bounded_value_range_raises_not_supported(self):
        # ValueRange with a bounded offset must be rejected by Django before
        # reaching YDB, because YDB does not support bounded RANGE frames.
        self._insert(pk=1, bounty=30_000_000)

        with self.assertRaises(NotSupportedError):
            list(
                WindowTestModel.objects.annotate(
                    w=Window(
                        Sum("bounty"),
                        order_by="id",
                        frame=ValueRange(start=-1, end=0),
                    )
                )
            )
