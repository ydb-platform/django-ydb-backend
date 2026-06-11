from django.db import connection
from django.test import TransactionTestCase

from .models import Article
from .models import BigBox
from .models import BigItem
from .models import Club
from .models import IntTag
from .models import Member
from .models import Membership
from .models import StrBox
from .models import StrItem
from .models import UuidBox
from .models import UuidItem


def _column_types(table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor, table_name
        )
    return {field.name: field.type_code for field in description}


def _target_relation_column(through, target_model):
    for field in through._meta.fields:
        if field.is_relation and field.remote_field.model is target_model:
            return field.column
    message = f"no relation column to {target_model!r}"
    raise AssertionError(message)


class TestAutoCreatedM2M(TransactionTestCase):
    databases = {"default"}

    def test_auto_through_table_exists(self):
        through_table = Article.tags.through._meta.db_table
        self.assertIn(through_table, connection.introspection.table_names())

    def test_add_list_remove(self):
        article = Article.objects.create(title="Backends")
        ydb = IntTag.objects.create(name="ydb")
        django = IntTag.objects.create(name="django")

        article.tags.add(ydb, django)
        self.assertEqual(
            set(article.tags.values_list("name", flat=True)),
            {"ydb", "django"},
        )

        # Reverse accessor goes through the same auto-created table.
        self.assertIn(article, ydb.articles.all())

        article.tags.remove(ydb)
        self.assertEqual(
            list(article.tags.values_list("name", flat=True)),
            ["django"],
        )

        article.tags.clear()
        self.assertEqual(article.tags.count(), 0)

    def test_no_foreign_key_constraints_reported(self):
        through_table = Article.tags.through._meta.db_table
        with connection.cursor() as cursor:
            self.assertEqual(
                connection.introspection.get_relations(cursor, through_table), {}
            )

    def test_through_columns_integer_target(self):
        through = Article.tags.through
        column = _target_relation_column(through, IntTag)
        types = _column_types(through._meta.db_table)
        self.assertEqual(types[column], "Int32")

    def test_through_columns_string_target(self):
        through = StrBox.items.through
        column = _target_relation_column(through, StrItem)
        types = _column_types(through._meta.db_table)
        self.assertEqual(types[column], "Utf8")

    def test_through_columns_uuid_target(self):
        through = UuidBox.items.through
        column = _target_relation_column(through, UuidItem)
        types = _column_types(through._meta.db_table)
        self.assertEqual(types[column], "UUID")

    def test_through_columns_big_integer_target(self):
        through = BigBox.items.through
        column = _target_relation_column(through, BigItem)
        types = _column_types(through._meta.db_table)
        self.assertEqual(types[column], "Int64")

    def test_string_pk_m2m_round_trip(self):
        box = StrBox.objects.create(name="box")
        item = StrItem.objects.create(code="ABC")
        box.items.add(item)
        self.assertIn(item, box.items.all())


class TestCustomThroughM2M(TransactionTestCase):
    databases = {"default"}

    def test_custom_through_is_a_regular_table(self):
        # A user-defined through model is created as an ordinary model, not as
        # an auto-created M2M table.
        self.assertFalse(Member.clubs.through._meta.auto_created)
        self.assertIn(
            Membership._meta.db_table, connection.introspection.table_names()
        )

    def test_custom_through_round_trip(self):
        member = Member.objects.create(name="Ada")
        club = Club.objects.create(name="Pioneers")
        Membership.objects.create(member=member, club=club, role="founder")

        self.assertIn(club, member.clubs.all())
        self.assertIn(member, club.members.all())
        self.assertEqual(
            Membership.objects.get(member=member, club=club).role, "founder"
        )
