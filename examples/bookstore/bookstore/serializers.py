from rest_framework import serializers

from .models import Author
from .models import Book
from .models import Category


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "bio"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class BookSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "author_name",
            "categories",
            "owner",
            "description",
            "price",
            "quantity",
            "limited_edition",
            "release_date",
            "created_at",
        ]
        read_only_fields = ["owner", "created_at"]
