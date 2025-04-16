from django.test import SimpleTestCase

from .models import Book


class TestInsert(SimpleTestCase):
    databases = {"default"}

    def test_insert(self):
        books = [
            {
                "title": "Moby-Dick",
                "author": "Herman Melville",
                "isbn": "9780451528298",
                "price": 320,
            },
            {
                "title": "Jane Eyre",
                "author": "Charlotte Bronte",
                "isbn": "9781420937116",
                "price": 280,
            },
            {
                "title": "Weathering Heights",
                "author": "Emily Bronte",
                "isbn": "9781537964693",
                "price": 310,
            },
            {
                "title": "Three Comrades",
                "author": "Erich Maria Remarque",
                "isbn": "978-544670",
                "price": 1000,
            },
            {
                "title": "Lord of the Flies",
                "author": "William Golding",
                "isbn": "978-0393315796",
                "price": 330,
            },
        ]

        for book_info in books:
            Book.objects.create(**book_info)

        books = Book.objects.all()
        isbns = [book.isbn for book in books]

        self.assertTrue(books.count() > 0)
        self.assertIn("9780451528298", isbns)
        self.assertIn("9781420937116", isbns)
        self.assertIn("9781537964693", isbns)
        self.assertIn("978-544670", isbns)
        self.assertIn("978-0393315796", isbns)

    def test_bulk_insert(self):
        books = [
            Book(
                title="War and piece",
                author="Lev Tolstoy",
                isbn="9780679783305",
                price=550,
            ),
            Book(
                title="Crime and punishment",
                author="Fedor Dostoevsky",
                isbn="9785445303873",
                price=400,
            ),
        ]

        Book.objects.bulk_create(books)
        books = Book.objects.all()
        isbns = [book.isbn for book in books]

        self.assertTrue(books.count() > 0)
        self.assertIn("9780679783305", isbns)
        self.assertIn("9785445303873", isbns)
