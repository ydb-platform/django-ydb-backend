"""
Regression tests for issue #44: auto-increment primary keys are read back with
INSERT ... RETURNING (the actual generated ids), not by selecting MAX(pk) and
assuming contiguous ids.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from django.test import TransactionTestCase

from type.models import NullableFieldsModel
from type.models import TimeModel

from .models import EventRecord
from .models import Product


class TestInsertReturning(TransactionTestCase):
    databases = {"default"}

    def test_single_auto_pk(self):
        obj = EventRecord.objects.create(name="one")
        self.assertIsNotNone(obj.pk)
        self.assertEqual(EventRecord.objects.get(name="one").pk, obj.pk)

    def test_bulk_auto_pk_sets_each_pk(self):
        objs = EventRecord.objects.bulk_create(
            [EventRecord(name=f"b{i}") for i in range(5)]
        )
        pks = [o.pk for o in objs]
        self.assertTrue(all(pk is not None for pk in pks))
        self.assertEqual(len(set(pks)), 5)
        # Each returned pk maps to the right row (order preserved).
        for obj in objs:
            self.assertEqual(EventRecord.objects.get(pk=obj.pk).name, obj.name)

    def test_returned_pk_is_own_not_global_max(self):
        # A pre-existing row with a high pk (as a concurrent writer would leave)
        # must not be mistaken for this insert's generated id.
        EventRecord.objects.create(pk=999999, name="high")
        obj = EventRecord.objects.create(name="mine")
        self.assertNotEqual(obj.pk, 999999)
        self.assertEqual(EventRecord.objects.get(name="mine").pk, obj.pk)

    def test_explicit_pk_single(self):
        obj = EventRecord.objects.create(pk=777, name="explicit")
        self.assertEqual(obj.pk, 777)
        self.assertTrue(EventRecord.objects.filter(pk=777).exists())

    def test_explicit_pk_bulk(self):
        objs = EventRecord.objects.bulk_create(
            [EventRecord(pk=100 + i, name=f"e{i}") for i in range(3)]
        )
        self.assertEqual([o.pk for o in objs], [100, 101, 102])
        self.assertEqual(
            EventRecord.objects.filter(pk__in=[100, 101, 102]).count(), 3
        )

    def test_non_auto_pk(self):
        obj = Product.objects.create(
            sku="ABC", name="x", category="c", price=1, stock=1
        )
        self.assertEqual(obj.pk, "ABC")

    def test_nullable_bulk(self):
        objs = NullableFieldsModel.objects.bulk_create(
            [
                NullableFieldsModel(int_field=1, char_field=None),
                NullableFieldsModel(int_field=None, char_field="x"),
            ]
        )
        self.assertTrue(all(o.pk is not None for o in objs))
        self.assertEqual(len({o.pk for o in objs}), 2)
        self.assertEqual(NullableFieldsModel.objects.count(), 2)

    def test_temporal_values_bulk(self):
        moment = datetime(2023, 5, 15, 14, 30, tzinfo=timezone.utc)
        objs = TimeModel.objects.bulk_create(
            [
                TimeModel(
                    date_field=date(2023, 5, 15),
                    datetime_field=moment,
                    duration_field=timedelta(hours=2),
                ),
                TimeModel(
                    date_field=date(2024, 1, 1),
                    datetime_field=moment,
                    duration_field=timedelta(days=1),
                ),
            ]
        )
        self.assertTrue(all(o.pk is not None for o in objs))
        self.assertEqual(TimeModel.objects.count(), 2)
