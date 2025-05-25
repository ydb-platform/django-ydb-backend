from django.test import SimpleTestCase

from .models import TextRelatedModel


class TextRelatedFieldsTest(SimpleTestCase):
    databases = {"default"}

    def test_char_field_utf8(self):
        test_cases = [
            "Обычный текст",
            "汉字",
            "日本語",
            "😊🌟",
            "العربية",
            "a" * 255,
        ]

        for text in test_cases:
            with self.subTest(text=text):
                obj = TextRelatedModel.objects.create(
                    char_field=text,
                    text_field=f"test text {text}"
                )
                fetched = TextRelatedModel.objects.get(pk=obj.pk)
                self.assertEqual(fetched.char_field, text)
                self.assertIsInstance(fetched.char_field, str)

    def test_text_field_utf8(self):
        test_cases = [
            "Длинный текст кириллицей " * 10,
            "漢字漢字漢字" * 100,
            "😊🌟" * 50 + "✅" * 50,
            "ab" * 5000,
        ]

        for text in test_cases:
            with self.subTest(text=text[:50]):
                obj = TextRelatedModel.objects.create(
                    char_field="Head",
                    text_field=text
                )
                fetched = TextRelatedModel.objects.get(pk=obj.pk)
                self.assertEqual(fetched.text_field, text)
                self.assertIsInstance(fetched.text_field, str)

    def test_empty_values(self):
        obj = TextRelatedModel.objects.create(
            char_field="",
            text_field=""
        )
        fetched = TextRelatedModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.char_field, "")
        self.assertEqual(fetched.text_field, "")

    def test_update_operations(self):
        obj = TextRelatedModel.objects.create(
            char_field="old head",
            text_field="old content"
        )

        TextRelatedModel.objects.filter(pk=obj.pk).update(
            char_field="new head",
            text_field="new content"
        )

        obj.refresh_from_db()

        self.assertEqual(obj.char_field, "new head")
        self.assertEqual(obj.text_field, "new content")
