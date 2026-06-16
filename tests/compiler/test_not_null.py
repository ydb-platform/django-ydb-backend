from django.db import IntegrityError
from django.test import TransactionTestCase

from .models import Book


class NotNullViolationTest(TransactionTestCase):
    """A NULL in a NOT NULL column surfaces as IntegrityError, not the driver's
    opaque type error (see compiler._get_data)."""

    def test_insert_null_into_not_null_field_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            Book.objects.create(isbn="N1", title="t", author="a", price=None)
