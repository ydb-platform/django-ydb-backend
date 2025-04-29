from django import forms

from .models import BookStore


class BookStoreForm(forms.ModelForm):
    class Meta:
        model = BookStore
        fields = [
            "title",
            "author",
            "description",
            "quantity",
            "release_dt",
            "price",
            "limited_edition",
        ]
