from django.test import TransactionTestCase

from .models import SimpleItem


class TestExists(TransactionTestCase):
    """
    QuerySet.exists() compiles to ``SELECT (1) ... WHERE ... LIMIT 1`` where the
    leading ``Value(1)`` is a parameter placeholder with no backing column. The
    select compiler must keep that placeholder aligned with the WHERE operands
    instead of dropping it.
    """

    databases = {"default"}

    def setUp(self):
        SimpleItem.objects.create(
            code="A100", category="electronics", quantity=5, in_stock=True
        )
        SimpleItem.objects.create(
            code="B200", category="furniture", quantity=0, in_stock=False
        )

    def test_exists_without_filter(self):
        self.assertTrue(SimpleItem.objects.exists())

    def test_exists_with_charfield_filter(self):
        self.assertTrue(SimpleItem.objects.filter(category="electronics").exists())
        self.assertFalse(SimpleItem.objects.filter(category="books").exists())

    def test_exists_with_integerfield_filter(self):
        self.assertTrue(SimpleItem.objects.filter(quantity=5).exists())
        self.assertFalse(SimpleItem.objects.filter(quantity=999).exists())

    def test_exists_with_booleanfield_filter(self):
        self.assertTrue(SimpleItem.objects.filter(in_stock=True).exists())
        self.assertTrue(SimpleItem.objects.filter(in_stock=False).exists())

    def test_exists_with_combined_filter(self):
        self.assertTrue(
            SimpleItem.objects.filter(category="electronics", quantity=5).exists()
        )
        self.assertFalse(
            SimpleItem.objects.filter(category="electronics", quantity=0).exists()
        )
