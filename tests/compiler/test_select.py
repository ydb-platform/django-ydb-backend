from django.test import TransactionTestCase

from .models import Product
from .models import ProductReview
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


class TestSlicedSubquery(TransactionTestCase):
    """
    Slicing a subquery emits LIMIT/OFFSET inside it. YQL rejects a bare OFFSET
    (it must follow a LIMIT), so qs[N:] -- an offset with no upper bound -- gets
    a default LIMIT (and a warning), else "mismatched input 'OFFSET'".
    """

    databases = {"default"}

    def setUp(self):
        product = Product.objects.create(
            sku="P1", name="p", category="c", price=1, stock=1
        )
        # Ratings 0..4; ids ascend with creation order.
        self.ids = [
            ProductReview.objects.create(product=product, rating=r).id
            for r in range(5)
        ]

    def _filter_in(self, sliced):
        return set(
            ProductReview.objects.filter(id__in=sliced).values_list(
                "id", flat=True
            )
        )

    def test_limit_only_subquery(self):
        # [:2] -> LIMIT 2: the two highest ids.
        sub = ProductReview.objects.order_by("-id")[:2]
        self.assertEqual(self._filter_in(sub), set(self.ids[3:]))

    def test_limit_and_offset_subquery(self):
        # [1:3] -> LIMIT 2 OFFSET 1: skip the highest id, take the next two.
        sub = ProductReview.objects.order_by("-id")[1:3]
        self.assertEqual(self._filter_in(sub), {self.ids[2], self.ids[3]})

    def test_offset_only_subquery(self):
        # [2:] -> OFFSET with no upper bound: a default LIMIT is applied (and a
        # warning emitted); drops the two highest ids.
        sub = ProductReview.objects.order_by("-id")[2:]
        with self.assertWarns(UserWarning):
            self.assertEqual(self._filter_in(sub), set(self.ids[:3]))

    def test_offset_only_outer_query(self):
        # The same on a top-level query, not just a subquery.
        with self.assertWarns(UserWarning):
            got = list(
                ProductReview.objects.order_by("-id")[2:].values_list(
                    "id", flat=True
                )
            )
        self.assertEqual(got, self.ids[:3][::-1])

    def test_empty_slice(self):
        # qs[5:5] is LIMIT 0 (limit is 0, not "no limit"): it must return
        # nothing, not fall into the offset-default path and return rows.
        self.assertEqual(list(ProductReview.objects.order_by("-id")[5:5]), [])
