from django.db.models import F
from django.test import TransactionTestCase

from .models import Book


class PatternEscapingTest(TransactionTestCase):
    """`%`, `_` and `\\` in a lookup value are matched literally (issue #75)."""

    def setUp(self):
        self.under = Book.objects.create(
            isbn="1", title="Article_ with underscore", author="x", price=1
        )
        self.pct = Book.objects.create(
            isbn="2", title="Article% with percent", author="x", price=1
        )
        self.backslash = Book.objects.create(
            isbn="3", title="Article with \\ backslash", author="x", price=1
        )
        self.plain = Book.objects.create(
            isbn="4", title="Article plain", author="x", price=1
        )

    def test_startswith_matches_literal_underscore(self):
        self.assertCountEqual(
            Book.objects.filter(title__startswith="Article_"),
            [self.under],
        )

    def test_startswith_matches_literal_percent(self):
        self.assertCountEqual(
            Book.objects.filter(title__startswith="Article%"),
            [self.pct],
        )

    def test_contains_matches_literal_backslash(self):
        self.assertCountEqual(
            Book.objects.filter(title__contains="\\"),
            [self.backslash],
        )

    def test_startswith_without_specials_matches_all(self):
        self.assertCountEqual(
            Book.objects.filter(title__startswith="Article"),
            [self.under, self.pct, self.backslash, self.plain],
        )

    def test_icontains_matches_literal_underscore(self):
        self.assertCountEqual(
            Book.objects.filter(title__icontains="article_"),
            [self.under],
        )


class PatternLookupExpressionTest(TransactionTestCase):
    """Pattern lookups with an expression (column) RHS use pattern_ops/pattern_esc."""

    def test_contains_startswith_endswith_with_column(self):
        a = Book.objects.create(
            isbn="20", title="hello world", author="hello", price=1
        )
        b = Book.objects.create(
            isbn="21", title="say hello", author="hello", price=1
        )
        c = Book.objects.create(
            isbn="22", title="well hello there", author="hello", price=1
        )
        self.assertCountEqual(Book.objects.filter(title__startswith=F("author")), [a])
        self.assertCountEqual(Book.objects.filter(title__endswith=F("author")), [b])
        self.assertCountEqual(
            Book.objects.filter(title__contains=F("author")), [a, b, c]
        )

    def test_column_expression_escapes_special_chars(self):
        # The author value carries a literal '%'; it must be escaped on the
        # database side (pattern_esc), not treated as a LIKE wildcard.
        literal = Book.objects.create(
            isbn="23", title="10% off", author="10%", price=1
        )
        Book.objects.create(isbn="24", title="10X off", author="10%", price=1)
        self.assertCountEqual(
            Book.objects.filter(title__startswith=F("author")), [literal]
        )
