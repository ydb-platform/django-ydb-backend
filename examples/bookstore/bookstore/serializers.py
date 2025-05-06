from rest_framework import serializers
from .models import BookStore


class BookStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookStore
        fields = '__all__'
