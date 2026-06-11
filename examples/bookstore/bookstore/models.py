from django.conf import settings
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    # ForeignKey: stored as a plain `author_id` column (YDB has no FK
    # constraints; on_delete is enforced by Django's ORM, not the database).
    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="books"
    )
    # ManyToManyField: backed by an auto-created through table.
    categories = models.ManyToManyField(
        Category, related_name="books", blank=True
    )
    # Links a book to the auth user that created it.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
    )
    description = models.TextField(blank=True, default="")
    price = models.PositiveIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=0)
    limited_edition = models.BooleanField(default=False)
    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
