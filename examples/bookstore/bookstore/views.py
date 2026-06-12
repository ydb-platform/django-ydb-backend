from rest_framework import filters
from rest_framework import permissions
from rest_framework import viewsets

from .models import Author
from .models import Book
from .models import Category
from .serializers import AuthorSerializer
from .serializers import BookSerializer
from .serializers import CategorySerializer


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
