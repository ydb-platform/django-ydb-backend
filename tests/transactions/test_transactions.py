from django.db import connection
from django.db import transaction
from django.db.transaction import TransactionManagementError
from django.test import TransactionTestCase

from .models import TxItem


class TestAtomic(TransactionTestCase):
    databases = {"default"}

    def test_commit(self):
        with transaction.atomic():
            TxItem.objects.create(name="a")
        self.assertEqual(TxItem.objects.filter(name="a").count(), 1)

    def test_rollback_on_exception(self):
        with self.assertRaises(ValueError), transaction.atomic():
            TxItem.objects.create(name="b")
            raise ValueError
        self.assertEqual(TxItem.objects.filter(name="b").count(), 0)

    def test_set_rollback(self):
        with transaction.atomic():
            TxItem.objects.create(name="c")
            transaction.set_rollback(True)
        self.assertEqual(TxItem.objects.filter(name="c").count(), 0)

    def test_nested_atomic_outer_rollback(self):
        with self.assertRaises(ValueError), transaction.atomic():
            TxItem.objects.create(name="outer")
            with transaction.atomic():
                TxItem.objects.create(name="inner")
            raise ValueError
        self.assertEqual(TxItem.objects.count(), 0)

    def test_connection_usable_after_error(self):
        with self.assertRaises(ValueError), transaction.atomic():
            TxItem.objects.create(name="d")
            raise ValueError
        self.assertEqual(TxItem.objects.filter(name="d").count(), 0)
        TxItem.objects.create(name="ok")
        self.assertEqual(TxItem.objects.filter(name="ok").count(), 1)

    def test_inner_atomic_caught_exception_breaks_transaction(self):
        # No savepoints: a caught exception inside a nested atomic marks the
        # whole transaction for rollback, so further queries are rejected.
        with self.assertRaises(TransactionManagementError), transaction.atomic():
            try:
                with transaction.atomic():
                    TxItem.objects.create(name="x")
                    raise ValueError  # noqa: TRY301
            except ValueError:
                pass
            TxItem.objects.count()
        self.assertEqual(TxItem.objects.count(), 0)

    def test_ddl_inside_atomic_raises(self):
        # YDB cannot roll back DDL (can_rollback_ddl=False), so schema changes
        # inside an atomic block are rejected.
        with self.assertRaises(TransactionManagementError), transaction.atomic(), \
                connection.schema_editor() as editor:
            editor.create_model(TxItem)
