from django.core.paginator import Paginator
from django.test import TransactionTestCase

from .models import Book


class PaginatorTest(TransactionTestCase):
    databases = {"default"}

    def test_count_pages_and_slicing(self):
        for i in range(5):
            Book.objects.create(isbn=f"pag-{i}", title=f"t{i}", author="a", price=i)
        paginator = Paginator(
            Book.objects.filter(isbn__startswith="pag-").order_by("isbn"), 2
        )
        self.assertEqual(paginator.count, 5)
        self.assertEqual(paginator.num_pages, 3)
        self.assertEqual(
            [b.isbn for b in paginator.page(1).object_list], ["pag-0", "pag-1"]
        )
        self.assertEqual(
            [b.isbn for b in paginator.page(2).object_list], ["pag-2", "pag-3"]
        )
        self.assertEqual(
            [b.isbn for b in paginator.page(3).object_list], ["pag-4"]
        )
