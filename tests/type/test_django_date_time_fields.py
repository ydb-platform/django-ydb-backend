from datetime import date
from datetime import datetime
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .models import TimeModel


class TimeFieldsTest(SimpleTestCase):
    databases = {"default"}

    def setUp(self):
        self.obj = TimeModel.objects.create(
            date_field=date(2023, 1, 1),
            datetime_field=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
            duration_field=timedelta(days=1)
        )

    def test_date_field(self):
        test_date = date(2023, 5, 15)
        obj = TimeModel.objects.create(
            date_field=test_date,
            datetime_field=datetime(2023, 5, 15, 12, 0, tzinfo=timezone.utc),
            duration_field=timedelta(days=1)
        )

        fetched = TimeModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.date_field, test_date)
        self.assertIsInstance(fetched.date_field, date)

    def test_datetime_field(self):
        aware_datetime = datetime(2023, 5, 15, 12, 30, 45, tzinfo=timezone.utc)

        obj = TimeModel.objects.create(
            date_field=date(2023, 5, 15),
            datetime_field=aware_datetime,
            duration_field=timedelta(hours=2)
        )

        fetched = TimeModel.objects.get(pk=obj.pk)
        self.assertEqual(
            fetched.datetime_field,
            aware_datetime.replace(tzinfo=None)
        )

    def test_duration_field(self):
        test_duration = timedelta(days=5, hours=12, minutes=30)
        obj = TimeModel.objects.create(
            date_field=date(2023, 5, 15),
            datetime_field=datetime(2023, 5, 15, 12, 0, tzinfo=timezone.utc),
            duration_field=test_duration
        )

        fetched = TimeModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.duration_field, test_duration)
        self.assertIsInstance(fetched.duration_field, timedelta)

        negative_duration = timedelta(days=-1)
        obj.duration_field = negative_duration
        obj.save()
        fetched.refresh_from_db()
        self.assertEqual(fetched.duration_field, negative_duration)

        large_duration = timedelta(days=10000)
        obj.duration_field = large_duration
        obj.save()
        fetched.refresh_from_db()
        self.assertEqual(fetched.duration_field, large_duration)

    def test_combined_fields(self):
        test_data = {
            "date_field": date(2023, 12, 31),
            "datetime_field":  datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            "duration_field": timedelta(days=365)
        }

        obj = TimeModel.objects.create(**test_data)
        fetched = TimeModel.objects.get(pk=obj.pk)

        self.assertEqual(
            fetched.date_field,
            test_data["date_field"]
        )
        self.assertEqual(
            fetched.datetime_field,
            test_data["datetime_field"].replace(tzinfo=None)
        )
        self.assertEqual(
            fetched.duration_field,
            test_data["duration_field"]
        )

    def test_update_date_field(self):
        new_date = date(2023, 12, 31)
        TimeModel.objects.filter(pk=self.obj.pk).update(date_field=new_date)
        self.obj.refresh_from_db()

        self.assertEqual(self.obj.date_field, new_date)
        self.assertIsInstance(self.obj.date_field, date)

    def test_update_datetime_field(self):
        new_datetime = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        TimeModel.objects.filter(pk=self.obj.pk).update(datetime_field=new_datetime)
        self.obj.refresh_from_db()

        self.assertEqual(
            self.obj.datetime_field,
            new_datetime.replace(tzinfo=None)
        )

    def test_update_duration_field(self):
        new_duration = timedelta(days=30, hours=12)
        TimeModel.objects.filter(pk=self.obj.pk).update(duration_field=new_duration)
        self.obj.refresh_from_db()

        self.assertEqual(self.obj.duration_field, new_duration)
        self.assertIsInstance(self.obj.duration_field, timedelta)

    def test_update_all_fields(self):
        update_data = {
            "date_field": date(2024, 1, 1),
            "datetime_field": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "duration_field": timedelta(days=365)
        }

        TimeModel.objects.filter(pk=self.obj.pk).update(**update_data)
        self.obj.refresh_from_db()

        self.assertEqual(
            self.obj.date_field,
            update_data["date_field"]
        )
        self.assertEqual(
            self.obj.datetime_field,
            update_data["datetime_field"].replace(tzinfo=None)
        )
        self.assertEqual(
            self.obj.duration_field,
            update_data["duration_field"]
        )
