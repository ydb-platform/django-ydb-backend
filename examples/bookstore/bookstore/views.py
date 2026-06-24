from django.shortcuts import redirect
from django.shortcuts import render
from rest_framework import filters
from rest_framework import permissions
from rest_framework import viewsets

from .models import Author
from .models import Book
from .models import Category
from .serializers import AuthorSerializer
from .serializers import BookSerializer
from .serializers import CategorySerializer


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def book_list(request):
    """A small server-rendered page: list the books and add one via a form.

    A plain Django view (template + ORM) alongside the REST API, to show the
    traditional request/response path working on YDB. Adding a book creates the
    author (and an optional category) on the fly.
    """
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        author_name = request.POST.get("author", "").strip()
        if title and author_name:
            author, _ = Author.objects.get_or_create(name=author_name)
            book = Book.objects.create(
                title=title,
                author=author,
                price=_to_int(request.POST.get("price")),
                quantity=_to_int(request.POST.get("quantity")),
                owner=request.user if request.user.is_authenticated else None,
            )
            category_name = request.POST.get("category", "").strip()
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)
                book.categories.add(category)
        return redirect("book_list")

    books = Book.objects.select_related("author").prefetch_related("categories")
    return render(request, "bookstore/book_list.html", {"books": books})


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("author").prefetch_related(
        "categories"
    )
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author__name"]
    ordering_fields = ["title", "price", "quantity", "release_date", "created_at"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
