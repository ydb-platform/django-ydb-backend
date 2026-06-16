from django.db.models import F
from django.db.models.functions import Substr
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


class SubstrTest(TransactionTestCase):
    """Substr() on a Utf8 column, 1-indexed (issue #87)."""

    def test_substr_is_one_indexed(self):
        obj = Book.objects.annotate(
            head=Substr("author", 1, 3),
            tail=Substr("author", 4),
        ).get(
            isbn=Book.objects.create(
                isbn="40", title="t", author="abcdef", price=1
            ).isbn
        )
        self.assertEqual(obj.head, "abc")
        self.assertEqual(obj.tail, "def")

    def test_pattern_lookup_with_substr(self):
        a = Book.objects.create(
            isbn="41", title="John Smith", author="Johx", price=1
        )
        b = Book.objects.create(
            isbn="42", title="Rhonda Simpson", author="sonx", price=1
        )
        # Substr(author, 1, 3) is "Joh" / "son".
        self.assertCountEqual(
            Book.objects.filter(title__startswith=Substr("author", 1, 3)), [a]
        )
        self.assertCountEqual(
            Book.objects.filter(title__contains=Substr("author", 1, 3)), [a, b]
        )
        self.assertCountEqual(
            Book.objects.filter(title__endswith=Substr("author", 1, 3)), [b]
        )


class PatternLookupNullableExpressionTest(TransactionTestCase):
    """An expression RHS over a nullable column (issue #91).

    The LIKE pattern is then ``Optional<Utf8>``, which YQL rejects; pattern_esc
    COALESCEs it to a non-optional Utf8 and a guard ensures a NULL right-hand
    side excludes the row rather than matching every row (empty pattern).
    """

    def test_substr_over_nullable_column(self):
        a = Book.objects.create(
            isbn="50", title="John Smith", author="x", alias="Johx", price=1
        )
        b = Book.objects.create(
            isbn="51", title="Rhonda Simpson", author="x", alias="sonx", price=1
        )
        # alias is NULL: Substr(alias, 1, 3) is NULL and must match nothing, not
        # collapse to an empty pattern that matches every row.
        Book.objects.create(
            isbn="52", title="anything", author="x", alias=None, price=1
        )
        self.assertCountEqual(
            Book.objects.filter(title__startswith=Substr("alias", 1, 3)), [a]
        )
        self.assertCountEqual(
            Book.objects.filter(title__icontains=Substr("alias", 1, 3)), [a, b]
        )
        self.assertCountEqual(
            Book.objects.filter(title__endswith=Substr("alias", 1, 3)), [b]
        )

    def test_null_column_rhs_excludes_row(self):
        match = Book.objects.create(
            isbn="53", title="hello world", author="x", alias="hello", price=1
        )
        # A NULL alias must not match, even though its column is the RHS.
        Book.objects.create(
            isbn="54", title="hello world", author="x", alias=None, price=1
        )
        self.assertCountEqual(
            Book.objects.filter(title__startswith=F("alias")), [match]
        )
