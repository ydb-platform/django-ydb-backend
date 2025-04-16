from django.db.models import Q
from django.test import TransactionTestCase

from .models import SimpleItem


class TestDelete(TransactionTestCase):
    databases = {"default"}

    def test_delete_single(self):
        SimpleItem.objects.create(
            code="A100",
            category="electronics",
            quantity=5,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="B200",
            category="furniture",
            quantity=0,
            in_stock=False,
        )
        SimpleItem.objects.create(
            code="C300",
            category="clothing",
            quantity=12,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="D400",
            category="electronics",
            quantity=3,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="E500",
            category="books",
            quantity=7,
            in_stock=False,
        )
        SimpleItem.objects.create(
            code="F600",
            category="clothing",
            quantity=0,
            in_stock=False,
        )
        SimpleItem.objects.create(
            code="G700",
            category="books",
            quantity=1,
            in_stock=True,
        )

        initial_count = SimpleItem.objects.count()
        SimpleItem.objects.get(code="A100").delete()

        self.assertEqual(SimpleItem.objects.count(), initial_count - 1)
        self.assertEqual(SimpleItem.objects.filter(code="A100").count(), 0)

    def test_delete_complex_condition(self):
        SimpleItem.objects.create(
            code="G500",
            category="books",
            quantity=2,
            in_stock=False,
        )
        SimpleItem.objects.create(
            code="H600",
            category="clothing",
            quantity=4,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="I700",
            category="books",
            quantity=1,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="L700",
            category="furniture",
            quantity=1,
            in_stock=True,
        )

        SimpleItem.objects.filter(
            (Q(category="books") & Q(quantity__lt=5)) | Q(category="furniture")
        ).delete()

        self.assertEqual(SimpleItem.objects.count(), 1)

    def test_delete_all(self):
        SimpleItem.objects.create(
            code="U600",
            category="clothing",
            quantity=4,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="Z700",
            category="books",
            quantity=1,
            in_stock=True,
        )
        SimpleItem.objects.create(
            code="X700",
            category="furniture",
            quantity=1,
            in_stock=True,
        )

        SimpleItem.objects.all().delete()
        self.assertEqual(SimpleItem.objects.count(), 0)
