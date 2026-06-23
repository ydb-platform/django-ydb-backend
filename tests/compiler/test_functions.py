import math

from django.db.models.functions import Pi
from django.db.models.functions import Random
from django.test import TransactionTestCase

from .models import Book


class PiFunctionTest(TransactionTestCase):
    """Pi() maps to YQL's Math::Pi() (no PI() built-in); issue #80."""

    def test_pi(self):
        Book.objects.create(isbn="60", title="t", author="a", price=1)
        value = Book.objects.annotate(p=Pi()).get(isbn="60").p
        self.assertAlmostEqual(value, math.pi, places=5)


class RandomFunctionTest(TransactionTestCase):
    """Random() maps to YQL's Random(...) (no zero-arg RANDOM()); issue #80."""

    def test_random_scalar(self):
        # YQL's Random needs an argument; the backend anchors the scalar form on
        # CurrentUtcTimestamp() so it yields a Double in [0, 1).
        Book.objects.create(isbn="61", title="t", author="a", price=1)
        value = Book.objects.annotate(r=Random()).get(isbn="61").r
        self.assertGreaterEqual(value, 0.0)
        self.assertLess(value, 1.0)

    def test_random_ordering(self):
        # order_by("?") orders by Random(<pk>, CurrentUtcTimestamp()); a
        # query-constant random cannot be ordered by, so the pk anchors it.
        for i in range(4):
            Book.objects.create(isbn=f"7{i}", title="t", author="a", price=1)
        self.assertEqual(len(list(Book.objects.order_by("?"))), 4)
