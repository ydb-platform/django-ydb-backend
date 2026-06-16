import math

from django.db.models.functions import Pi
from django.test import TransactionTestCase

from .models import Book


class PiFunctionTest(TransactionTestCase):
    """Pi() maps to YQL's Math::Pi() (no PI() built-in); issue #80."""

    def test_pi(self):
        Book.objects.create(isbn="60", title="t", author="a", price=1)
        value = Book.objects.annotate(p=Pi()).get(isbn="60").p
        self.assertAlmostEqual(value, math.pi, places=5)
