from django.test import SimpleTestCase

from .models import JSONModel


class JSONFieldTest(SimpleTestCase):
    databases = {"default"}

    def test_dict_roundtrip(self):
        obj = JSONModel.objects.create(data={"key": "value", "num": 42})
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.data, {"key": "value", "num": 42})

    def test_list_roundtrip(self):
        obj = JSONModel.objects.create(data=[1, "two", 3.0, None])
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.data, [1, "two", 3.0, None])

    def test_nested_roundtrip(self):
        payload = {"outer": {"inner": [1, 2, {"deep": True}]}, "empty": {}}
        obj = JSONModel.objects.create(data=payload)
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.data, payload)

    def test_scalar_string(self):
        obj = JSONModel.objects.create(data="hello")
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.data, "hello")

    def test_scalar_integer(self):
        obj = JSONModel.objects.create(data=99)
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.data, 99)

    def test_boolean_true(self):
        obj = JSONModel.objects.create(data=True)
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertIs(fetched.data, True)

    def test_boolean_false(self):
        obj = JSONModel.objects.create(data=False)
        fetched = JSONModel.objects.get(pk=obj.pk)
        self.assertIs(fetched.data, False)

    def test_update(self):
        obj = JSONModel.objects.create(data={"v": 1})
        JSONModel.objects.filter(pk=obj.pk).update(data={"v": 2, "new": "field"})
        obj.refresh_from_db()
        self.assertEqual(obj.data, {"v": 2, "new": "field"})
