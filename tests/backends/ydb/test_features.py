"""
Tests for DatabaseFeatures.

Flag values are consolidated into a single assertion test.
Behavioral tests verify that YDB actually behaves as each flag claims.
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
# Flag value assertions — one test to catch accidental changes
# ---------------------------------------------------------------------------


class TestFeatureFlags(SimpleTestCase):
    def test_all_flag_values(self):
        f = connection.features
        # group by
        self.assertFalse(f.allows_group_by_selected_pks)
        self.assertFalse(f.allows_group_by_select_index)
        # update / delete
        self.assertFalse(f.update_can_self_select)
        self.assertFalse(f.delete_can_self_reference_subquery)
        # null / string semantics
        self.assertFalse(f.interprets_empty_strings_as_nulls)
        self.assertTrue(f.ignores_table_name_case)
        # unique / nullable constraints
        self.assertFalse(f.supports_nullable_unique_constraints)
        self.assertFalse(f.supports_partially_nullable_unique_constraints)
        self.assertFalse(f.allows_multiple_constraints_on_same_fields)
        # bulk insert
        self.assertTrue(f.can_return_rows_from_bulk_insert)
        self.assertFalse(f.supports_ignore_conflicts)
        # transactions / savepoints
        self.assertTrue(f.supports_transactions)
        self.assertFalse(f.uses_savepoints)
        self.assertFalse(f.supports_forward_references)
        # native types
        self.assertTrue(f.has_native_uuid_field)
        self.assertTrue(f.has_native_duration_field)
        self.assertTrue(f.has_native_json_field)
        self.assertFalse(f.has_json_object_function)
        self.assertTrue(f.supports_temporal_subtraction)
        self.assertTrue(f.json_key_contains_list_matching_requires_list)
        # regex / timezone
        self.assertFalse(f.supports_regex_backreferencing)
        self.assertFalse(f.has_zoneinfo_database)
        # ordering
        self.assertFalse(f.supports_order_by_nulls_modifier)
        # auto pk
        self.assertFalse(f.allows_auto_pk_0)
        self.assertFalse(f.supports_sequence_reset)
        # introspection
        self.assertFalse(f.can_introspect_default)
        self.assertFalse(f.can_introspect_foreign_keys)
        self.assertFalse(f.can_introspect_check_constraints)
        self.assertFalse(f.can_introspect_json_field)
        self.assertFalse(f.supports_index_column_ordering)
        # schema / DDL
        self.assertTrue(f.schema_editor_uses_clientside_param_binding)
        self.assertFalse(f.supports_foreign_keys)
        self.assertFalse(f.can_create_inline_fk)
        self.assertTrue(f.can_rename_index)
        self.assertFalse(f.indexes_foreign_keys)
        self.assertFalse(f.supports_column_check_constraints)
        self.assertFalse(f.supports_table_check_constraints)
        self.assertFalse(f.supports_expression_defaults)
        self.assertFalse(f.supports_default_keyword_in_insert)
        self.assertFalse(f.supports_default_keyword_in_bulk_insert)
        # select variants
        self.assertFalse(f.supports_select_for_update_with_limit)
        self.assertFalse(f.supports_select_intersection)
        self.assertFalse(f.supports_select_difference)
        self.assertFalse(f.supports_parentheses_in_compound)
        # window functions
        self.assertTrue(f.supports_over_clause)
        self.assertTrue(f.only_supports_unbounded_with_preceding_and_following)
        # indexes
        self.assertFalse(f.supports_partial_indexes)
        self.assertFalse(f.supports_functions_in_partial_indexes)
        self.assertTrue(f.supports_covering_indexes)
        self.assertFalse(f.supports_expression_indexes)
        # collation
        self.assertFalse(f.supports_collation_on_charfield)
        self.assertFalse(f.supports_collation_on_textfield)
        self.assertFalse(f.supports_non_deterministic_collations)

    # --- RANGE frame behavior: these test Django ops, not just flag values ---

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
        start, end = connection.ops.window_frame_rows_start_end(start=-1, end=0)
        self.assertEqual(start, "1 PRECEDING")
        self.assertEqual(end, "CURRENT ROW")


# ---------------------------------------------------------------------------
# Shared model for behavioral integration tests
# ---------------------------------------------------------------------------


class BehaviorTestModel(models.Model):
    id = models.IntegerField(primary_key=True)
    bounty = models.IntegerField()
    name = models.CharField(max_length=200, null=True)  # noqa: DJ001

    class Meta:
        app_label = "backends"
        db_table = "ydb_feat_behavior"
        managed = False

    def __str__(self):
        return str(self.id)


class BehaviorTestMixin:
    def setUp(self):
        try:
            with connection.schema_editor() as ed:
                ed.delete_model(BehaviorTestModel)
        except Exception:  # noqa: BLE001
            pass
        with connection.schema_editor() as ed:
            ed.create_model(BehaviorTestModel)

    def tearDown(self):
        try:
            with connection.schema_editor() as ed:
                ed.delete_model(BehaviorTestModel)
        except Exception:  # noqa: BLE001
            pass
        super().tearDown()


# ---------------------------------------------------------------------------
# Behavioral: operations that must raise NotSupportedError
# ---------------------------------------------------------------------------


class TestUnsupportedOperations(BehaviorTestMixin, TransactionTestCase):
    """
    Verify that flags set to False actually cause NotSupportedError when the
    corresponding operation is attempted, not just that the flag value is False.
    """

    databases = {"default"}

    def test_intersection_raises_not_supported(self):
        qs = BehaviorTestModel.objects.all()
        with self.assertRaises(NotSupportedError):
            list(qs.intersection(qs))

    def test_difference_raises_not_supported(self):
        qs = BehaviorTestModel.objects.all()
        with self.assertRaises(NotSupportedError):
            list(qs.difference(qs))

    def test_ignore_conflicts_raises_not_supported(self):
        with self.assertRaises(NotSupportedError):
            BehaviorTestModel.objects.bulk_create(
                [BehaviorTestModel(id=1, bounty=0)],
                ignore_conflicts=True,
            )


# ---------------------------------------------------------------------------
# Behavioral: operations that must succeed
# ---------------------------------------------------------------------------


class TestSupportedBehavior(BehaviorTestMixin, TransactionTestCase):
    """
    Verify that flags set to True reflect actual YDB behavior.
    """

    databases = {"default"}

    def test_empty_string_is_not_null(self):
        # interprets_empty_strings_as_nulls = False:
        # storing '' must not become NULL.
        BehaviorTestModel.objects.create(id=1, bounty=0, name="")
        obj = BehaviorTestModel.objects.get(id=1)
        self.assertEqual(obj.name, "")
        self.assertFalse(
            BehaviorTestModel.objects.filter(id=1, name__isnull=True).exists()
        )

    def test_transactions_commit_data(self):
        # supports_transactions = True: data written inside atomic() is visible
        # after the block closes.
        from django.db import transaction

        with transaction.atomic():
            BehaviorTestModel.objects.create(id=1, bounty=1_500_000_000)  # Whitebeard

        self.assertTrue(BehaviorTestModel.objects.filter(id=1).exists())

    def test_transactions_rollback_on_exception(self):
        # supports_transactions = True: data written inside a rolled-back
        # atomic() must not be visible afterwards.
        from django.db import transaction

        with self.assertRaises(ValueError), transaction.atomic():
            BehaviorTestModel.objects.create(id=2, bounty=1_000_000_000)  # Roger
            raise ValueError("rollback")

        self.assertFalse(BehaviorTestModel.objects.filter(id=2).exists())


# ---------------------------------------------------------------------------
# Window function ORM integration tests
# ---------------------------------------------------------------------------


WindowTestModel = BehaviorTestModel


class TestWindowFunctions(BehaviorTestMixin, TransactionTestCase):
    databases = {"default"}

    def _insert(self, pk, bounty):
        BehaviorTestModel.objects.create(id=pk, bounty=bounty)

    def test_unbounded_rows_frame_cumulative_sum(self):
        self._insert(pk=1, bounty=30_000_000)   # Luffy
        self._insert(pk=2, bounty=320_000_000)  # Zoro
        self._insert(pk=3, bounty=66_000_000)   # Nami

        table = BehaviorTestModel._meta.db_table
        qs = (
            BehaviorTestModel.objects
            .annotate(running=Window(Sum("bounty"), order_by="id"))
            .values_list("id", "running")
            .order_by("id")
        )
        # Assert only the OVER clause — the surrounding SELECT format varies
        # across Django versions (4.2 omits AS alias on the pk column).
        self.assertIn(
            f"SUM(`{table}`.`bounty`) OVER (ORDER BY `{table}`.`id`) AS `running`",
            str(qs.query),
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

        table = BehaviorTestModel._meta.db_table
        qs = (
            BehaviorTestModel.objects
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
        self.assertIn(
            f"SUM(`{table}`.`bounty`) OVER"
            f" (ORDER BY `{table}`.`id` ROWS BETWEEN 1 PRECEDING AND CURRENT ROW)"
            f" AS `sliding`",
            str(qs.query),
        )
        rows = list(qs)
        self.assertEqual(rows[0][1], 30_000_000)            # only Luffy
        self.assertEqual(rows[1][1], 350_000_000)           # Luffy + Zoro
        self.assertEqual(rows[2][1], 386_000_000)           # Zoro + Nami

    def test_bounded_value_range_raises_not_supported(self):
        # ValueRange with bounded offset must be rejected before reaching YDB.
        self._insert(pk=1, bounty=30_000_000)

        with self.assertRaises(NotSupportedError):
            list(
                BehaviorTestModel.objects.annotate(
                    w=Window(
                        Sum("bounty"),
                        order_by="id",
                        frame=ValueRange(start=-1, end=0),
                    )
                )
            )
