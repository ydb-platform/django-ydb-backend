from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone as stdlib_timezone

from django.db.models.functions import TruncDate
from django.db.models.functions import TruncDay
from django.db.models.functions import TruncHour
from django.db.models.functions import TruncMonth
from django.db.models.functions import TruncYear
from django.test import SimpleTestCase
from django.test import TransactionTestCase
from django.utils import timezone

from .models import AlarmModel
from .models import TimeModel


class TimeFieldsTest(SimpleTestCase):
    databases = {"default"}

    def setUp(self):
        self.obj = TimeModel.objects.create(
            date_field=date(2025, 1, 1),
            datetime_field=datetime(2025, 1, 1, 12, 0, tzinfo=stdlib_timezone.utc),
            duration_field=timedelta(days=1)
        )

    def test_date_field(self):
        test_date = date(2025, 5, 15)

        obj = TimeModel.objects.create(
            date_field=test_date,
            datetime_field=datetime(2025, 5, 15, 12, 0, tzinfo=stdlib_timezone.utc),
            duration_field=timedelta(days=1)
        )

        fetched = TimeModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.date_field, test_date)
        self.assertIsInstance(fetched.date_field, date)

    def test_datetime_field(self):
        aware_datetime = datetime(2025, 5, 15, 12, 30, 45, tzinfo=stdlib_timezone.utc)

        obj = TimeModel.objects.create(
            date_field=date(2025, 5, 15),
            datetime_field=aware_datetime,
            duration_field=timedelta(hours=2)
        )

        fetched = TimeModel.objects.get(pk=obj.pk)
        self.assertEqual(
            fetched.datetime_field,
            aware_datetime.replace(tzinfo=None)
        )

    def test_datetime_microsecond_precision(self):
        # DateTimeField maps to YDB Timestamp, which keeps microseconds; the
        # older Datetime mapping truncated values to whole seconds.
        aware_datetime = datetime(
            2025, 5, 15, 12, 30, 45, 123456, tzinfo=stdlib_timezone.utc
        )

        obj = TimeModel.objects.create(
            date_field=date(2025, 5, 15),
            datetime_field=aware_datetime,
            duration_field=timedelta(hours=1),
        )

        fetched = TimeModel.objects.get(pk=obj.pk)
        self.assertEqual(
            fetched.datetime_field, aware_datetime.replace(tzinfo=None)
        )
        self.assertEqual(fetched.datetime_field.microsecond, 123456)

    def test_duration_field(self):
        test_duration = timedelta(days=5, hours=12, minutes=30)

        obj = TimeModel.objects.create(
            date_field=date(2025, 5, 15),
            datetime_field=datetime(2025, 5, 15, 12, 0, tzinfo=stdlib_timezone.utc),
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
            "date_field": date(2025, 12, 31),
            "datetime_field": datetime(
                2025, 12, 31, 23, 59, 59, tzinfo=stdlib_timezone.utc
            ),
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
        new_date = date(2025, 12, 31)

        TimeModel.objects.filter(pk=self.obj.pk).update(date_field=new_date)
        self.obj.refresh_from_db()

        self.assertEqual(self.obj.date_field, new_date)
        self.assertIsInstance(self.obj.date_field, date)

    def test_update_datetime_field(self):
        new_datetime = datetime(2025, 12, 31, 23, 59, 59, tzinfo=stdlib_timezone.utc)

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
            "date_field": date(2026, 1, 1),
            "datetime_field": datetime(2026, 1, 1, 0, 0, 0, tzinfo=stdlib_timezone.utc),
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

    def test_str_representation(self):
        obj = TimeModel.objects.get(id=self.obj.id)
        expected_str = (
            f"Date: {obj.date_field} | "
            f"Datetime: {obj.datetime_field} | "
            f"Duration: {obj.duration_field}"
        )
        self.assertEqual(str(obj), expected_str)

    def test_datetime_field_timezone(self):
        obj = TimeModel.objects.get(id=self.obj.id)
        moscow_time = obj.datetime_field.astimezone(
            timezone.get_current_timezone()
        )
        self.assertIsNotNone(moscow_time.tzinfo)

    def test_datetime_field_truncate(self):
        TimeModel.objects.create(
            date_field=date(2010, 2, 17),
            datetime_field=datetime(2016, 12, 5, 12, 0, tzinfo=stdlib_timezone.utc),
            duration_field=timedelta(days=365)
        )

        obj = TimeModel.objects.annotate(
            date_only=TruncDate("datetime_field")
        ).get(date_field=date(2010, 2, 17))
        self.assertEqual(obj.date_only, date(2016, 12, 5))

    def test_date_field_truncate(self):
        # Exercises date_trunc_sql (DateField -> MakeDate). StartOf* returns a
        # Resource the driver cannot read, so the result must be materialised
        # back to a Date (issue #93).
        TimeModel.objects.all().delete()
        TimeModel.objects.create(
            date_field=date(1980, 4, 23),
            datetime_field=datetime(1980, 4, 23, 9, 30, tzinfo=stdlib_timezone.utc),
            duration_field=timedelta(days=1),
        )
        obj = TimeModel.objects.annotate(
            d_year=TruncYear("date_field"),
            d_month=TruncMonth("date_field"),
            d_day=TruncDay("date_field"),
        ).get()
        self.assertEqual(obj.d_year, date(1980, 1, 1))
        self.assertEqual(obj.d_month, date(1980, 4, 1))
        self.assertEqual(obj.d_day, date(1980, 4, 23))

    def test_dates_distinct(self):
        # QuerySet.dates() builds SELECT DISTINCT <truncated date> ORDER BY the
        # alias. Regression for issue #93: before the fix the ORDER BY term
        # re-referenced the base column the DISTINCT projection had dropped.
        TimeModel.objects.all().delete()
        for d in (date(1980, 4, 23), date(1980, 4, 23), date(2005, 7, 27)):
            TimeModel.objects.create(
                date_field=d,
                datetime_field=datetime(
                    d.year, d.month, d.day, tzinfo=stdlib_timezone.utc
                ),
                duration_field=timedelta(days=1),
            )
        self.assertEqual(
            list(TimeModel.objects.dates("date_field", "day")),
            [date(1980, 4, 23), date(2005, 7, 27)],
        )
        self.assertEqual(
            list(TimeModel.objects.dates("date_field", "month")),
            [date(1980, 4, 1), date(2005, 7, 1)],
        )

    def test_datetime_field_truncate_units(self):
        # Exercises datetime_trunc_sql (DateTimeField -> MakeTimestamp).
        # Truncation happens in the active timezone; pin it to UTC for a
        # deterministic result.
        TimeModel.objects.all().delete()
        TimeModel.objects.create(
            date_field=date(2016, 12, 5),
            datetime_field=datetime(
                2016, 12, 5, 14, 30, 15, tzinfo=stdlib_timezone.utc
            ),
            duration_field=timedelta(days=1),
        )
        with timezone.override(stdlib_timezone.utc):
            obj = TimeModel.objects.annotate(
                t_month=TruncMonth("datetime_field"),
                t_hour=TruncHour("datetime_field"),
            ).get()
        self.assertEqual(
            obj.t_month, datetime(2016, 12, 1, tzinfo=stdlib_timezone.utc)
        )
        self.assertEqual(
            obj.t_hour, datetime(2016, 12, 5, 14, 0, tzinfo=stdlib_timezone.utc)
        )

    def test_field_components(self):
        TimeModel.objects.create(
            date_field=date(2023, 5, 15),
            datetime_field=datetime(
                2023, 5, 15, 14, 30, 15, tzinfo=stdlib_timezone.utc
            ),
            duration_field=timedelta(hours=2, minutes=30)
        )
        TimeModel.objects.create(
            date_field=date(2024, 12, 31),
            datetime_field=datetime(
                2024, 12, 31, 23, 59, 45, tzinfo=stdlib_timezone.utc
            ),
            duration_field=timedelta(days=1, seconds=3600)
        )

        obj_dt = TimeModel.objects.get(date_field=date(2023, 5, 15))
        obj_dttm = TimeModel.objects.get(datetime_field__year=2023)
        obj_dur = TimeModel.objects.get(duration_field=timedelta(hours=2, minutes=30))

        self.assertEqual(obj_dt.date_field.year, 2023)
        self.assertEqual(obj_dt.date_field.month, 5)
        self.assertEqual(obj_dt.date_field.day, 15)
        self.assertEqual(obj_dttm.datetime_field.hour, 14)
        self.assertEqual(obj_dttm.datetime_field.minute, 30)
        self.assertEqual(obj_dur.duration_field.total_seconds(), 9000)
        self.assertEqual(obj_dur.duration_field.seconds, 9000)

    def test_duration_field_arithmetic(self):
        obj = TimeModel.objects.create(
            date_field=date(1987, 3, 4),
            datetime_field=datetime(2002, 1, 1, 12, 0, tzinfo=stdlib_timezone.utc),
            duration_field=timedelta(days=1)
        )

        obj = TimeModel.objects.get(id=obj.id)
        new_duration = obj.duration_field * 2
        self.assertEqual(new_duration, timedelta(days=2))

    def test_date_field_arithmetic(self):
        obj = TimeModel.objects.create(
            date_field=date(1997, 3, 4),
            datetime_field=datetime(2012, 2, 4, 12, 0, tzinfo=stdlib_timezone.utc),
            duration_field=timedelta(days=1)
        )

        new_date = obj.date_field + timedelta(days=10)
        self.assertEqual(new_date, date(1997, 3, 14))

    # def test_datetime_field_queries(self):
    #     qs = TimeModel.objects.filter(datetime_field__hour='12')
    #     self.assertEqual(qs.count(), 1)
    #     self.assertEqual(qs.first().datetime_field.minute, 30)
    # def test_date_field_queries(self):
    #     qs = TimeModel.objects.filter(date_field__year=2023, date_field__month=5)
    #     self.assertEqual(qs.count(), 1)
    #     self.assertEqual(qs.first().date_field, date(2023, 5, 15))


class TimeFieldLookupTest(TransactionTestCase):
    """__hour/__minute/__second on a TimeField (issue #81).

    TimeField is stored as Int64 microseconds since midnight, so the components
    are extracted with integer arithmetic rather than DateTime::Get*.
    """

    databases = {"default"}

    def setUp(self):
        self.early = AlarmModel.objects.create(desc="Early", time=time(5, 30))
        self.late = AlarmModel.objects.create(desc="Late", time=time(10, 0))
        self.precise = AlarmModel.objects.create(
            desc="Precise", time=time(12, 34, 56)
        )

    def test_hour_lookup(self):
        self.assertCountEqual(
            AlarmModel.objects.filter(time__hour=5), [self.early]
        )

    def test_minute_lookup(self):
        self.assertCountEqual(
            AlarmModel.objects.filter(time__minute=30), [self.early]
        )

    def test_second_lookup(self):
        self.assertCountEqual(
            AlarmModel.objects.filter(time__second=56), [self.precise]
        )
