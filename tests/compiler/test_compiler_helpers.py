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
    """
    _generate_params_for_update takes a per-placeholder list of Django internal
    field types (or None) and produces typed YDB parameters.
    """

    def test_datetime_object_is_converted_to_timestamp(self):
        import ydb
        dt = datetime(2025, 6, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            internal_types=["DateTimeField"],
            params=(dt,),
        )
        ts, ydb_type = result["$p1"]
        # Epoch microseconds (YDB Timestamp), so sub-second precision survives.
        self.assertEqual(ts, int(round(dt.timestamp() * 1_000_000)))
        self.assertEqual(ts % 1_000_000, 123456)
        self.assertEqual(ydb_type, ydb.PrimitiveType.Timestamp)

    def test_extract_int_uses_int32_type(self):
        # filter(field__month=1) compares an integer against a DateTimeField.
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            internal_types=["DateTimeField"],
            params=(1,),
        )
        stored, ydb_type = result["$p1"]
        self.assertEqual(stored, 1)
        self.assertEqual(ydb_type, ydb.PrimitiveType.Int32)

    def test_non_datetime_field_is_passed_through(self):
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1", "$p2"],
            internal_types=["CharField", "AutoField"],
            params=("Alice", 42),
        )
        self.assertEqual(result["$p1"], ("Alice", ydb.PrimitiveType.Utf8))
        self.assertEqual(result["$p2"], (42, ydb.PrimitiveType.Int32))

    def test_mixed_set_and_where(self):
        # UPDATE t SET name = %s WHERE occurred_at = %s
        ts = int(datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        result = _generate_params_for_update(
            placeholder_rows=["$p1", "$p2"],
            internal_types=["CharField", "DateTimeField"],
            params=("Bob", ts),
        )
        self.assertEqual(result["$p1"][0], "Bob")
        self.assertEqual(result["$p2"][0], ts)

    def test_temporal_value_with_non_temporal_type_uses_value(self):
        # A __year lookup types its datetime bounds from an IntegerField
        # output_field; the contradiction must fall back to value typing.
        import ydb
        dt = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            internal_types=["IntegerField"],
            params=(dt,),
        )
        stored, ydb_type = result["$p1"]
        self.assertEqual(stored, int(round(dt.timestamp() * 1_000_000)))
        self.assertEqual(ydb_type, ydb.PrimitiveType.Timestamp)


class TestGenerateParamsForUpdateUnresolvedType(SimpleTestCase):
    """Placeholders with no resolvable field type fall back to value typing."""

    def test_unresolved_type_is_typed_from_value(self):
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            internal_types=[None],
            params=(1,),
        )
        self.assertEqual(result["$p1"], (1, ydb.PrimitiveType.Int64))

    def test_types_stay_aligned_with_placeholders(self):
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1", "$p2"],
            internal_types=[None, "IntegerField"],
            params=(1, 30),
        )
        self.assertEqual(result["$p1"], (1, ydb.PrimitiveType.Int64))
        self.assertEqual(result["$p2"], (30, ydb.PrimitiveType.Int32))

    def test_type_without_ydb_mapping_falls_back_to_value(self):
        # EmailField has no entry in _ydb_types; the string value -> Utf8.
        import ydb
        result = _generate_params_for_update(
            placeholder_rows=["$p1"],
            internal_types=["EmailField"],
            params=("a@example.com",),
        )
        self.assertEqual(result["$p1"], ("a@example.com", ydb.PrimitiveType.Utf8))

    def test_uninferable_value_raises(self):
        with self.assertRaises(ValueError):
            _generate_params_for_update(
                placeholder_rows=["$p1"],
                internal_types=[None],
                params=(object(),),
            )


class TestGetDataDateTimeField(SimpleTestCase):
    """Regression tests for _get_data with int timestamps."""

    def test_datetime_object_is_converted(self):
        dt = datetime(2025, 3, 10, 8, 0, 0, 654321, tzinfo=timezone.utc)
        field = _make_field("occurred_at", "DateTimeField")
        result = _get_data([field], [[dt]])
        # Epoch microseconds (YDB Timestamp), preserving sub-second precision.
        self.assertEqual(
            result[0]["occurred_at"], int(round(dt.timestamp() * 1_000_000))
        )
        self.assertEqual(result[0]["occurred_at"] % 1_000_000, 654321)

    def test_int_timestamp_is_passed_through(self):
        ts = int(datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc).timestamp())
        field = _make_field("occurred_at", "DateTimeField")
        result = _get_data([field], [[ts]])
        self.assertEqual(result[0]["occurred_at"], ts)

    def test_non_datetime_field_unchanged(self):
        field = _make_field("name", "CharField")
        result = _get_data([field], [["hello"]])
        self.assertEqual(result[0]["name"], "hello")
