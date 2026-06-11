"""
Unit tests for compiler helper functions.

These tests exercise _generate_params_for_update and _get_data directly
without a database connection, so they run as SimpleTestCase.
"""
from datetime import datetime
from datetime import timezone
from unittest.mock import MagicMock

from django.test import SimpleTestCase
from ydb_backend.models.sql.compiler import _generate_params_for_update
from ydb_backend.models.sql.compiler import _get_data


def _make_field(column, internal_type):
    field = MagicMock()
    field.column = column
    field.get_internal_type.return_value = internal_type
    field.remote_field = None
    return field


class TestGenerateParamsForUpdateDateTimeField(SimpleTestCase):
    """Regression tests for issue #54: int passed for DateTimeField must not crash."""

    def _field_types(self):
        return {
            "name": "CharField",
            "occurred_at": "DateTimeField",
            "id": "AutoField",
        }

    def test_datetime_object_is_converted_to_timestamp(self):
        import ydb
        dt = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            columns=["occurred_at"],
            field_types=self._field_types(),
            params=(dt,),
        )
        ts, ydb_type = result["$p1"]
        self.assertEqual(ts, int(dt.timestamp()))
        self.assertEqual(ydb_type, ydb.PrimitiveType.Datetime)

    def test_extract_int_uses_int32_type(self):
        # Regression for issue #54: filter(field__month=1) produces an integer
        # placeholder for a DateTimeField column.  The fix must not call
        # .timestamp() and must annotate the param as Int32, not Datetime.
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            columns=["occurred_at"],
            field_types=self._field_types(),
            params=(1,),
        )
        stored, ydb_type = result["$p1"]
        self.assertEqual(stored, 1)
        self.assertEqual(ydb_type, ydb.PrimitiveType.Int32)

    def test_int_timestamp_uses_int32_type(self):
        # When an int arrives for a DateTimeField (e.g. via Value(ts)), it is
        # passed through as Int32 — callers should use datetime objects instead.
        import ydb
        ts = int(datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc).timestamp())
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            columns=["occurred_at"],
            field_types=self._field_types(),
            params=(ts,),
        )
        stored, ydb_type = result["$p1"]
        self.assertEqual(stored, ts)
        self.assertEqual(ydb_type, ydb.PrimitiveType.Int32)

    def test_non_datetime_field_is_passed_through_unchanged(self):
        result = _generate_params_for_update(
            placeholder_rows=["$p1", "$p2"],
            columns=["name", "id"],
            field_types=self._field_types(),
            params=("Alice", 42),
        )
        self.assertEqual(result["$p1"][0], "Alice")
        self.assertEqual(result["$p2"][0], 42)

    def test_mixed_params_set_and_where(self):
        # Simulates: UPDATE t SET name = %s WHERE occurred_at = %s
        ts = int(datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        result = _generate_params_for_update(
            placeholder_rows=["$p1", "$p2"],
            columns=["name", "occurred_at"],
            field_types=self._field_types(),
            params=("Bob", ts),
        )
        self.assertEqual(result["$p1"][0], "Bob")
        self.assertEqual(result["$p2"][0], ts)


class TestGenerateParamsForUpdateUnresolvedColumn(SimpleTestCase):
    """
    Placeholders whose owning column cannot be resolved (column is None) must be
    typed from the parameter value and must stay positionally aligned with the
    remaining placeholders, instead of being dropped.
    """

    def _field_types(self):
        return {
            "quantity": "IntegerField",
            "id": "AutoField",
        }

    def test_unresolved_column_is_typed_from_value(self):
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            columns=[None],
            field_types=self._field_types(),
            params=(1,),
        )
        stored, ydb_type = result["$p1"]
        self.assertEqual(stored, 1)
        self.assertEqual(ydb_type, ydb.PrimitiveType.Int64)

    def test_unresolved_column_does_not_shift_following_params(self):
        # Mirrors QuerySet.exists(): SELECT (%s) ... WHERE quantity = %s
        # columns[0] is None (the literal Value(1) in the select list) and must
        # not consume the type that belongs to the WHERE placeholder.
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1", "$p2"],
            columns=[None, "quantity"],
            field_types=self._field_types(),
            params=(1, 30),
        )
        self.assertEqual(result["$p1"], (1, ydb.PrimitiveType.Int64))
        self.assertEqual(result["$p2"], (30, ydb.PrimitiveType.Int32))

    def test_unknown_column_falls_back_to_value_typing(self):
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            columns=["not_a_field"],
            field_types=self._field_types(),
            params=("hello",),
        )
        self.assertEqual(result["$p1"], ("hello", ydb.PrimitiveType.Utf8))

    def test_uninferable_value_raises(self):
        with self.assertRaises(ValueError):
            _generate_params_for_update(
                placeholder_rows=["$p1"],
                columns=[None],
                field_types=self._field_types(),
                params=(object(),),
            )


class TestGetDataDateTimeField(SimpleTestCase):
    """Regression tests for _get_data with int timestamps."""

    def test_datetime_object_is_converted(self):
        dt = datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc)
        field = _make_field("occurred_at", "DateTimeField")
        result = _get_data([field], [[dt]])
        self.assertEqual(result[0]["occurred_at"], int(dt.timestamp()))

    def test_int_timestamp_is_passed_through(self):
        ts = int(datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc).timestamp())
        field = _make_field("occurred_at", "DateTimeField")
        result = _get_data([field], [[ts]])
        self.assertEqual(result[0]["occurred_at"], ts)

    def test_non_datetime_field_unchanged(self):
        field = _make_field("name", "CharField")
        result = _get_data([field], [["hello"]])
        self.assertEqual(result[0]["name"], "hello")
