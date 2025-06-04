from decimal import Decimal
from math import isclose

from django.db.models import F
from django.test import SimpleTestCase

from .models import FloatingPointModel


class TestFloatingPointFields(SimpleTestCase):
    databases = {"default"}

    def test_valid_combined_values(self):
        obj1 = FloatingPointModel.objects.create(
            float_field=123.456,
            decimal_field=Decimal("123.456789012")
        )

        fetched1 = FloatingPointModel.objects.get(pk=obj1.pk)
        self.assertAlmostEqual(fetched1.float_field, 123.456, places=5)
        self.assertEqual(str(fetched1.decimal_field), "123.456789012")

        obj2 = FloatingPointModel.objects.create(
            float_field=3.4028235e+38,
            decimal_field=Decimal("0.000000001")
        )
        fetched2 = FloatingPointModel.objects.get(pk=obj2.pk)
        self.assertTrue(isclose(fetched2.float_field, 3.4028235e+38, rel_tol=1e-5))
        self.assertEqual(str(fetched2.decimal_field), "1E-9")

        obj3 = FloatingPointModel.objects.create(
            float_field=1.175494e-38,
            decimal_field=Decimal("999999999999.999999999")
        )
        fetched3 = FloatingPointModel.objects.get(pk=obj3.pk)
        self.assertAlmostEqual(fetched3.float_field, 1.175494e-38, places=6)
        self.assertEqual(str(fetched3.decimal_field), "999999999999.999999999")

        obj4 = FloatingPointModel.objects.create(
            float_field=0.0,
            decimal_field=Decimal("1234567890123.456789012")
        )
        fetched4 = FloatingPointModel.objects.get(pk=obj4.pk)
        self.assertEqual(fetched4.float_field, 0.0)
        self.assertEqual(str(fetched4.decimal_field), "1234567890123.456789012")

        obj5 = FloatingPointModel.objects.create(
            float_field=3.1415926535,
            decimal_field=Decimal("3.141592653")
        )
        fetched5 = FloatingPointModel.objects.get(pk=obj5.pk)
        self.assertAlmostEqual(fetched5.float_field, 3.1415926535, places=6)
        self.assertEqual(str(fetched5.decimal_field), "3.141592653")

    def test_bulk_insert(self):
        data = [
            FloatingPointModel(
                float_field=i * 1.1,
                decimal_field=Decimal(str(int(i) * i)),
            ) for i in range(1, 11)
        ]

        created = FloatingPointModel.objects.bulk_create(data)
        self.assertEqual(len(created), 10)
        self.assertEqual(created[-1].float_field, 11.0)

    def test_update(self):
        obj1 = FloatingPointModel.objects.create(
            float_field=123.456,
            decimal_field=Decimal("789.123456789")
        )
        obj2 = FloatingPointModel.objects.create(
            float_field=1.175494e-38,
            decimal_field=Decimal("0.000000001")
        )

        FloatingPointModel.objects.filter(pk=obj2.pk).update(
            float_field=987.654
        )
        updated = FloatingPointModel.objects.get(pk=obj2.pk)
        self.assertAlmostEqual(updated.float_field, 987.654, delta=1e-5)
        self.assertEqual(updated.decimal_field, Decimal("1E-9"))

        FloatingPointModel.objects.filter(pk=obj2.pk).update(
            decimal_field=Decimal("123456789.987654321")
        )
        updated = FloatingPointModel.objects.get(pk=obj2.pk)
        self.assertEqual(str(updated.decimal_field), "123456789.987654321")

        FloatingPointModel.objects.filter(pk=obj1.pk).update(
            float_field=3.14159265,
            decimal_field=Decimal("2.718281828")
        )
        updated = FloatingPointModel.objects.get(pk=obj1.pk)
        self.assertAlmostEqual(updated.float_field, 3.14159265, places=6)
        self.assertEqual(updated.decimal_field, Decimal("2.718281828"))

    def test_float_field_operations(self):
        obj = FloatingPointModel.objects.create(
            float_field=10.5,
            decimal_field=Decimal("3.141592653")
        )

        FloatingPointModel.objects.filter(pk=obj.pk).update(
            float_field=F("float_field") * 2 + 1
        )
        obj.refresh_from_db()
        self.assertAlmostEqual(obj.float_field, 22.0)

    def test_decimal_field_operations(self):
        obj = FloatingPointModel.objects.create(
            float_field=10.5,
            decimal_field=Decimal("10.5")
        )

        FloatingPointModel.objects.filter(pk=obj.pk).update(
            decimal_field=F("decimal_field") / Decimal("2.0") + Decimal("1.0")
        )
        obj.refresh_from_db()
        self.assertEqual(obj.decimal_field, Decimal("6.25"))
