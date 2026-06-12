from django.contrib import admin

from .models import Author
from .models import Book
from .models import Category


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "price", "quantity", "limited_edition"]
    list_filter = ["limited_edition", "categories"]
    search_fields = ["title", "author__name"]
    autocomplete_fields = ["author"]
    filter_horizontal = ["categories"]
