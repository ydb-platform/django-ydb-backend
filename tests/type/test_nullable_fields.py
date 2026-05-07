import datetime

from django.test import SimpleTestCase

from .models import NullableFieldsModel


class NullableFieldsTest(SimpleTestCase):
    databases = {"default"}

    def _create_all_null(self):
        return NullableFieldsModel.objects.create(
            char_field=None,
            int_field=None,
            big_int_field=None,
            float_field=None,
            bool_field=None,
            date_field=None,
            datetime_field=None,
            text_field=None,
        )

    def test_all_null_roundtrip(self):
        obj = self._create_all_null()
        fetched = NullableFieldsModel.objects.get(pk=obj.pk)
        self.assertIsNone(fetched.char_field)
        self.assertIsNone(fetched.int_field)
        self.assertIsNone(fetched.big_int_field)
        self.assertIsNone(fetched.float_field)
        self.assertIsNone(fetched.bool_field)
        self.assertIsNone(fetched.date_field)
        self.assertIsNone(fetched.datetime_field)
        self.assertIsNone(fetched.text_field)

    def test_char_field_null(self):
        obj = NullableFieldsModel.objects.create(char_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).char_field)

    def test_int_field_null(self):
        obj = NullableFieldsModel.objects.create(int_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).int_field)

    def test_big_int_field_null(self):
        obj = NullableFieldsModel.objects.create(big_int_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).big_int_field)

    def test_float_field_null(self):
        obj = NullableFieldsModel.objects.create(float_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).float_field)

    def test_bool_field_null(self):
        obj = NullableFieldsModel.objects.create(bool_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).bool_field)

    def test_date_field_null(self):
        obj = NullableFieldsModel.objects.create(date_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).date_field)

    def test_datetime_field_null(self):
        obj = NullableFieldsModel.objects.create(datetime_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).datetime_field)

    def test_text_field_null(self):
        obj = NullableFieldsModel.objects.create(text_field=None)
        self.assertIsNone(NullableFieldsModel.objects.get(pk=obj.pk).text_field)

    def test_non_null_values_roundtrip(self):
        obj = NullableFieldsModel.objects.create(
            char_field="hello",
            int_field=-42,
            big_int_field=10**15,
            float_field=3.14,
            bool_field=True,
            date_field=datetime.date(2024, 6, 15),
            datetime_field=datetime.datetime(
                2024, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc
            ),
            text_field="long text",
        )
        fetched = NullableFieldsModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.char_field, "hello")
        self.assertEqual(fetched.int_field, -42)
        self.assertEqual(fetched.big_int_field, 10**15)
        self.assertAlmostEqual(fetched.float_field, 3.14, places=5)
        self.assertIs(fetched.bool_field, True)
        self.assertEqual(fetched.date_field, datetime.date(2024, 6, 15))
        self.assertEqual(fetched.text_field, "long text")

    def test_isnull_filter(self):
        self._create_all_null()
        NullableFieldsModel.objects.create(int_field=1)
        self.assertGreaterEqual(
            NullableFieldsModel.objects.filter(int_field__isnull=True).count(), 1
        )
        self.assertGreaterEqual(
            NullableFieldsModel.objects.filter(int_field__isnull=False).count(), 1
        )
