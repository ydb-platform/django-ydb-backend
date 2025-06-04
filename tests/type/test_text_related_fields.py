from django.db.models import Avg
from django.db.models import Count
from django.db.models import F
from django.db.models import Q
from django.test import SimpleTestCase

from .models import BlogPost
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

    def test_field_string_concat(self):
        self.obj = TextRelatedModel.objects.create(
            char_field="Hello",
            text_field="This is a long text for testing purposes."
        )

        new_text_ch = self.obj.char_field + " World"
        new_text_txt = self.obj.text_field + " And more text added."

        self.assertEqual(new_text_ch, "Hello World")
        self.assertEqual(
            new_text_txt,
            "This is a long text for testing purposes. And more text added."
        )

    def test_char_field_search(self):
        TextRelatedModel.objects.create(
            char_field="Django is awesome",
            text_field="Django is a high-level Python web framework."
        )
        TextRelatedModel.objects.create(
            char_field="Python is great",
            text_field="Python is a popular programming language."
        )

        results_con = TextRelatedModel.objects.filter(char_field__contains="awesome")
        results_icon = TextRelatedModel.objects.filter(char_field__icontains="DJANGO")
        results_slike = TextRelatedModel.objects.filter(char_field__startswith="Django")
        results_elike = TextRelatedModel.objects.filter(char_field__endswith="great")

        self.assertEqual(results_con.count(), 1)
        self.assertEqual(results_con.first().char_field, "Django is awesome")

        self.assertEqual(results_icon.count(), 1)
        self.assertEqual(results_icon.first().char_field, "Django is awesome")

        self.assertEqual(results_slike.count(), 1)
        self.assertEqual(results_slike.first().char_field, "Django is awesome")

        self.assertEqual(results_elike.count(), 1)
        self.assertEqual(results_elike.first().char_field, "Python is great")

    def test_text_field_search(self):
        TextRelatedModel.objects.create(
            char_field="Object 1",
            text_field="The quick brown fox jumps over the lazy dog"
        )
        TextRelatedModel.objects.create(
            char_field="Object 2",
            text_field="Django ORM makes database queries easy"
        )
        TextRelatedModel.objects.create(
            char_field="Object 3",
            text_field="Regular expressions are powerful"
        )

        results_con = TextRelatedModel.objects.filter(
            text_field__contains="brown fox"
        )
        results_icon = TextRelatedModel.objects.filter(
            text_field__icontains="DJANGO orm"
        )
        results_slike = TextRelatedModel.objects.filter(
            text_field__startswith="The quick"
        )
        results_elike = TextRelatedModel.objects.filter(
            text_field__endswith="expressions are powerful"
        )
        results_reg = TextRelatedModel.objects.filter(
            text_field__regex=r"^The.*dog$"
        )
        results_ireg = TextRelatedModel.objects.filter(
            text_field__iregex=r"REGULAR\sEXPRESSIONS"
        )

        self.assertEqual(results_con.count(), 1)
        self.assertEqual(results_con.first().char_field, "Object 1")

        self.assertEqual(results_icon.count(), 1)
        self.assertEqual(results_icon.first().char_field, "Object 2")

        self.assertEqual(results_slike.count(), 1)
        self.assertEqual(results_slike.first().char_field, "Object 1")

        self.assertEqual(results_elike.count(), 1)
        self.assertEqual(results_elike.first().char_field, "Object 3")

        self.assertEqual(results_reg.count(), 1)
        self.assertEqual(results_reg.first().char_field, "Object 1")

        self.assertEqual(results_ireg.count(), 1)
        self.assertEqual(results_ireg.first().char_field, "Object 3")

    def test_combined_lookups(self):
        TextRelatedModel.objects.create(
            char_field="Spring Framework",
            text_field="Spring is a high-level Java web framework",
        )

        results = TextRelatedModel.objects.filter(
            char_field__icontains="spring",
            text_field__icontains="java"
        )

        self.assertEqual(results.count(), 1)

    def test_exact_vs_iexact(self):
        TextRelatedModel.objects.create(
            char_field="Molly is awesome",
            text_field="some text"
        )

        results1 = TextRelatedModel.objects.filter(
            char_field__exact="Molly is awesome"
        )
        results2 = TextRelatedModel.objects.filter(
            char_field__iexact="molly IS awesome"
        )

        self.assertEqual(results1.count(), 1)
        self.assertEqual(results2.count(), 1)

    def test_complex_queries(self):
        BlogPost.objects.bulk_create([
            BlogPost(
                title="Django для начинающих",
                content="Learning python. Django — it's a powerful framework",
                tags="django, web, python",
                views=100,
                is_published=True
            ),
            BlogPost(
                title="Python Advanced",
                content="Генераторы, декораторы и асинхронность в Python.",
                tags="python, advanced",
                views=50,
                is_published=True
            ),
            BlogPost(
                title="Web-development in 2024",
                content="Trends in web-development: Django, FastAPI, React.",
                tags="web, django, react",
                views=200,
                is_published=True
            ),
            BlogPost(
                title="Неопубликованный пост",
                content="Этот пост еще не опубликован.",
                tags="draft",
                views=10,
                is_published=False
            ),
            BlogPost(
                title="Django REST Framework",
                content="Create API with DRF.",
                tags="django, api, rest",
                views=150,
                is_published=True
            ),
            BlogPost(
                title="Hello World на Python",
                content="Simple program in Python",
                tags="python, beginner",
                views=300,
                is_published=True
            ),
            BlogPost(
                title="Тест Regex",
                content="Проверка 123-456 на соответствие шаблону.",
                tags="test, regex",
                views=5,
                is_published=False
            ),
        ])

        django_posts = BlogPost.objects.filter(
            tags__icontains="django",
            is_published=True
        )
        self.assertEqual(django_posts.count(), 3)

        popular_posts = BlogPost.objects.filter(
            (Q(title__icontains="python") | Q(title__icontains="django")),
            views__gt=100,
            is_published=True
        )
        self.assertEqual(popular_posts.count(), 2)

        digit_posts = BlogPost.objects.filter(content__regex=r"\d+")
        self.assertEqual(digit_posts.count(), 1)

        tag_stats = BlogPost.objects.filter(
            tags__icontains="python"
        ).aggregate(
            avg_views=Avg("views"),
            total_posts=Count("id")
        )
        self.assertEqual(tag_stats["total_posts"], 3)
        self.assertGreater(tag_stats["avg_views"], 50)

        BlogPost.objects.filter(
            tags__icontains="django"
        ).update(views=F("views") + 10)

        updated_post = BlogPost.objects.get(title="Django для начинающих")
        self.assertEqual(updated_post.views, 110)

        # annotated_posts = BlogPost.objects.annotate(
        #     title_length=Length("title"),
        #     title_with_views=Concat(
        #         "title", Value(" ("), "views", Value(" просмотров)"),
        #         output_field=CharField()
        #     )
        # ).filter(is_published=True)
        #
        # first_post = annotated_posts.first()
        # self.assertTrue(hasattr(first_post, "title_length"))
        # self.assertIn(" просмотров)", first_post.title_with_views)
