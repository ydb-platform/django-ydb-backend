from django.db import connection
from django.db.models import F
from django.test import SimpleTestCase

from .models import IntegerFieldsModel


class TestIntegerFields(SimpleTestCase):
    databases = {"default"}

    def test_integer_fields_min_max_ranges(self):
        obj = IntegerFieldsModel.objects.create(
            int_field=2147483647,
            big_int_field=9223372036854775807,
            small_int_field=32767,
            positive_int_field=4294967295,
            positive_big_int_field=18446744073709551615,
            positive_small_int_field=65535
        )

        self.assertEqual(obj.int_field, 2147483647)
        self.assertEqual(obj.big_int_field, 9223372036854775807)
        self.assertEqual(obj.small_int_field, 32767)
        self.assertEqual(obj.positive_int_field, 4294967295)
        self.assertEqual(obj.positive_big_int_field, 18446744073709551615)
        self.assertEqual(obj.positive_small_int_field, 65535)

        boundary_obj = IntegerFieldsModel.objects.create(
            int_field=-2147483648,
            big_int_field=-9223372036854775808,
            small_int_field=-32768,
            positive_int_field=0,
            positive_big_int_field=0,
            positive_small_int_field=0
        )

        self.assertEqual(boundary_obj.int_field, -2147483648)
        self.assertEqual(boundary_obj.big_int_field, -9223372036854775808)
        self.assertEqual(boundary_obj.small_int_field, -32768)
        self.assertEqual(boundary_obj.positive_int_field, 0)
        self.assertEqual(boundary_obj.positive_big_int_field, 0)
        self.assertEqual(boundary_obj.positive_small_int_field, 0)

    def test_db_schema(self):
        table_name = IntegerFieldsModel._meta.db_table

        with connection.cursor() as cursor:
            result = connection.introspection.get_table_description(
                cursor, table_name
            )

        int_actual = next(
            f.type_code for f in result if f.name == "int_field"
        )
        small_int_actual = next(
            f.type_code for f in result if f.name == "small_int_field"
        )
        big_int_actual = next(
            f.type_code for f in result if f.name == "big_int_field"
        )
        positive_int_actual = next(
            f.type_code for f in result if f.name == "positive_int_field"
        )
        positive_small_int_actual = next(
            f.type_code for f in result if f.name == "positive_small_int_field"
        )
        positive_big_int_actual = next(
            f.type_code for f in result if f.name == "positive_big_int_field"
        )

        self.assertEqual("Int16", small_int_actual)
        self.assertEqual("Int32", int_actual)
        self.assertEqual("Int64", big_int_actual)
        self.assertEqual("Uint16", positive_small_int_actual)
        self.assertEqual("Uint32", positive_int_actual)
        self.assertEqual("Uint64", positive_big_int_actual)

    def test_arithmetic_operations(self):
        IntegerFieldsModel.objects.all().delete()

        test_obj = IntegerFieldsModel.objects.create(
            int_field=100,
            big_int_field=1000,
            small_int_field=10,
            positive_int_field=50,
            positive_big_int_field=500,
            positive_small_int_field=5
        )

        results = IntegerFieldsModel.objects.annotate(
            int_mul=F("int_field") * 2,
            int_div=F("int_field") / 4,

            big_add=F("big_int_field") + 100,
            big_sub=F("big_int_field") - 500 + 675 - 12,

            small_mix=(F("small_int_field") * 3) + 5,

            pos_int_pow=F("positive_int_field") * F("positive_int_field"),

            pos_big_div=F("positive_big_int_field") / 2,

            pos_small_complex=(F("positive_small_int_field") + 10) * 2
        ).get(pk=test_obj.pk)

        self.assertEqual(results.int_mul, 200)
        self.assertAlmostEqual(results.int_div, 25.0)
        self.assertEqual(results.big_add, 1100)
        self.assertEqual(results.big_sub, 1163)
        self.assertEqual(results.small_mix, 35)
        self.assertEqual(results.pos_int_pow, 2500)
        self.assertAlmostEqual(results.pos_big_div, 250.0)
        self.assertEqual(results.pos_small_complex, 30)

        self.assertEqual(results.int_field, 100)
        self.assertEqual(results.big_int_field, 1000)
        self.assertEqual(results.small_int_field, 10)
        self.assertEqual(results.positive_int_field, 50)
        self.assertEqual(results.positive_big_int_field, 500)
        self.assertEqual(results.positive_small_int_field, 5)
