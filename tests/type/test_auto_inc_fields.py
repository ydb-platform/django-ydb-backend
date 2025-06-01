from django.db import connection
from django.test import TransactionTestCase

from .models import BigAutoIncModel
from .models import RegularAutoIncModel
from .models import SmallAutoIncModel


class TestAutoIncFields(TransactionTestCase):
    databases = {"default"}

    def test_auto_field_creation(self):
        small_obj = SmallAutoIncModel.objects.create(name="Test 1")
        regular_obj = RegularAutoIncModel.objects.create(name="Test 1")
        big_obj = BigAutoIncModel.objects.create(name="Test 1")

        self.assertIsNotNone(small_obj.small_id)
        self.assertIsNotNone(regular_obj.regular_id)
        self.assertIsNotNone(big_obj.big_id)

        self.assertEqual(small_obj.name, "Test 1")
        self.assertEqual(regular_obj.name, "Test 1")
        self.assertEqual(big_obj.name, "Test 1")

        self.assertIsInstance(small_obj.small_id, int)
        self.assertIsInstance(regular_obj.regular_id, int)
        self.assertIsInstance(big_obj.big_id, int)

    def test_auto_increment_behavior(self):
        small_obj1 = SmallAutoIncModel.objects.create(name="First")
        small_obj2 = SmallAutoIncModel.objects.create(name="Second")

        regular_obj1 = RegularAutoIncModel.objects.create(name="First")
        regular_obj2 = RegularAutoIncModel.objects.create(name="Second")

        big_obj1 = BigAutoIncModel.objects.create(name="First")
        big_obj2 = BigAutoIncModel.objects.create(name="Second")

        self.assertEqual(small_obj2.small_id, small_obj1.small_id + 1)
        self.assertEqual(regular_obj2.regular_id, regular_obj1.regular_id + 1)
        self.assertEqual(big_obj2.big_id, big_obj1.big_id + 1)

    def test_db_schema(self):
        small_table_name = SmallAutoIncModel._meta.db_table
        regular_table_name = RegularAutoIncModel._meta.db_table
        big_table_name = BigAutoIncModel._meta.db_table

        with connection.cursor() as cursor:
            small_result = connection.introspection.get_table_description(
                cursor, small_table_name
            )
            regular_result = connection.introspection.get_table_description(
                cursor, regular_table_name
            )
            big_result = connection.introspection.get_table_description(
                cursor, big_table_name
            )

        small_actual = next(
            f.type_code for f in small_result if f.name == "small_id"
        )
        regular_actual = next(
            f.type_code for f in regular_result if f.name == "regular_id"
        )
        big_actual = next(
            f.type_code for f in big_result if f.name == "big_id"
        )

        self.assertEqual("Int16", small_actual)
        self.assertEqual("Int32", regular_actual)
        self.assertEqual("Int64", big_actual)

    def test_bulk_create_with_auto_fields(self):
        small_objects = [SmallAutoIncModel(name=f"Obj {i}") for i in range(5)]
        SmallAutoIncModel.objects.bulk_create(small_objects)

        regular_objects = [RegularAutoIncModel(name=f"Obj {i}") for i in range(5)]
        RegularAutoIncModel.objects.bulk_create(regular_objects)

        big_objects = [BigAutoIncModel(name=f"Obj {i}") for i in range(5)]
        BigAutoIncModel.objects.bulk_create(big_objects)

        small_created = SmallAutoIncModel.objects.all()
        regular_created = RegularAutoIncModel.objects.all()
        big_created = BigAutoIncModel.objects.all()

        small_ids = [obj.small_id for obj in small_created]
        self.assertEqual(sorted(small_ids), small_ids)
        self.assertEqual(len(set(small_ids)), len(small_ids))

        regular_ids = [obj.regular_id for obj in regular_created]
        self.assertEqual(sorted(regular_ids), regular_ids)
        self.assertEqual(len(set(regular_ids)), len(regular_ids))

        big_ids = [obj.big_id for obj in big_created]
        self.assertEqual(sorted(big_ids), big_ids)
        self.assertEqual(len(set(big_ids)), len(big_ids))

    def test_auto_inc_with_create(self):
        SmallAutoIncModel.objects.create(small_id=-200, name="Test Small 2")
        RegularAutoIncModel.objects.create(regular_id=2147483641, name="Test Regular 2")
        BigAutoIncModel.objects.create(big_id=9223372036854775801, name="Test Big 2")

        self.assertEqual(
            SmallAutoIncModel.objects.get(small_id=-200).name,
            "Test Small 2"
        )
        self.assertEqual(
            RegularAutoIncModel.objects.get(regular_id=2147483641).name,
            "Test Regular 2"
        )
        self.assertEqual(
            BigAutoIncModel.objects.get(big_id=9223372036854775801).name,
            "Test Big 2"
        )

    def test_auto_field_sequence_after_manual_insert(self):
        SmallAutoIncModel.objects.create(small_id=32766, name="Manual Small")
        auto_obj = SmallAutoIncModel.objects.create(name="Auto Small")
        self.assertTrue(auto_obj.small_id >= 32766)
