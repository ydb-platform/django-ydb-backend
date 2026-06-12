"""
Regression tests for issue #37: query parameters are typed from Django's
expression tree (lookups / fields), not by regex-scanning the SQL. These cover
the cases the old heuristic was fragile for.
"""

from unittest import expectedFailure

from django.db.models import Case
from django.db.models import CharField
from django.db.models import Count
from django.db.models import Exists
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Value
from django.db.models import When
from django.test import TransactionTestCase

from type.models import NullableFieldsModel

from .models import Product
from .models import ProductReview


class TestParameterTyping(TransactionTestCase):
    databases = {"default"}

    def setUp(self):
        self.p1 = Product.objects.create(
            sku="A1", name="Phone", category="Electronics", price=999, stock=10
        )
        self.p2 = Product.objects.create(
            sku="A2", name="Cable", category="Electronics", price=20, stock=100
        )
        self.p3 = Product.objects.create(
            sku="B1", name="Book", category="Books", price=15, stock=5
        )
        ProductReview.objects.create(product=self.p1, rating=5)
        ProductReview.objects.create(product=self.p1, rating=4)
        ProductReview.objects.create(product=self.p3, rating=3)

    def test_fk_filter_join(self):
        ratings = ProductReview.objects.filter(
            product__category="Electronics"
        ).values_list("rating", flat=True)
        self.assertEqual(set(ratings), {5, 4})

    def test_fk_scalar_filter(self):
        self.assertEqual(
            ProductReview.objects.filter(product=self.p1).count(), 2
        )

    def test_in_filter(self):
        skus = Product.objects.filter(price__in=[999, 15]).values_list(
            "sku", flat=True
        )
        self.assertEqual(set(skus), {"A1", "B1"})

    def test_f_expression(self):
        skus = Product.objects.filter(price__gt=F("stock")).values_list(
            "sku", flat=True
        )
        self.assertEqual(set(skus), {"A1", "B1"})

    def test_case_when_annotation(self):
        tiers = dict(
            Product.objects.annotate(
                tier=Case(
                    When(price__gt=100, then=Value("hi")),
                    default=Value("lo"),
                    output_field=CharField(),
                )
            ).values_list("sku", "tier")
        )
        self.assertEqual(tiers, {"A1": "hi", "A2": "lo", "B1": "lo"})

    def test_value_annotation(self):
        count = (
            Product.objects.annotate(
                flag=Value(1, output_field=IntegerField())
            )
            .filter(flag=1)
            .count()
        )
        self.assertEqual(count, 3)

    def test_aggregate_having(self):
        groups = (
            Product.objects.values("category")
            .annotate(n=Count("sku"))
            .filter(n__gt=1)
        )
        self.assertEqual(
            [g["category"] for g in groups], ["Electronics"]
        )

    def test_in_subquery_noncorrelated(self):
        # A non-correlated subquery: its parameters are typed and compose into
        # the outer query (stock 5 matches a rating value of 5).
        skus = Product.objects.filter(
            stock__in=ProductReview.objects.values("rating")
        ).values_list("sku", flat=True)
        self.assertEqual(set(skus), {"B1"})

    # Correlated subqueries (OuterRef) are typed and compose correctly, but YDB
    # does not support correlated subqueries: the outer table is not in scope
    # inside the subquery ("Member not found"). This is a YDB platform
    # limitation, unrelated to parameter typing, and is kept here as a marker.
    @expectedFailure
    def test_exists_correlated(self):
        skus = Product.objects.filter(
            Exists(ProductReview.objects.filter(product=OuterRef("pk")))
        ).values_list("sku", flat=True)
        self.assertEqual(set(skus), {"A1", "B1"})

    @expectedFailure
    def test_subquery_correlated(self):
        top = Subquery(
            ProductReview.objects.filter(product=OuterRef("pk"))
            .order_by("-rating")
            .values("rating")[:1]
        )
        rating = (
            Product.objects.annotate(top_rating=top)
            .get(sku="A1")
            .top_rating
        )
        self.assertEqual(rating, 5)

    def test_update_with_where(self):
        updated = Product.objects.filter(category="Electronics").update(price=1)
        self.assertEqual(updated, 2)
        self.assertEqual(Product.objects.get(sku="A1").price, 1)

    def test_delete_with_where(self):
        # The WHERE parameter is typed from the field; the matching product and
        # its cascaded review are deleted, and the count is reported via
        # RETURNING.
        deleted, _ = Product.objects.filter(price__lt=20).delete()
        self.assertEqual(deleted, 2)
        self.assertFalse(Product.objects.filter(sku="B1").exists())
        self.assertEqual(Product.objects.count(), 2)

    def test_nullable_filter(self):
        NullableFieldsModel.objects.create(int_field=5)
        NullableFieldsModel.objects.create(int_field=None)
        self.assertEqual(
            NullableFieldsModel.objects.filter(int_field=5).count(), 1
        )
        self.assertEqual(
            NullableFieldsModel.objects.filter(int_field__isnull=True).count(), 1
        )
