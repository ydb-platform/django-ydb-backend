from django.db import models


class Book(models.Model):
    title = models.TextField()
    author = models.TextField(max_length=255)
    isbn = models.CharField(max_length=13, primary_key=True)
    price = models.IntegerField()

    def __str__(self):
        return f"{self.title} {self.author} {self.isbn} {self.price}"


class Product(models.Model):
    sku = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    price = models.IntegerField()
    stock = models.IntegerField()

    def __str__(self):
        return f"{self.sku} {self.name} {self.category} {self.price} {self.stock}"


class SimpleItem(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    category = models.CharField(max_length=30)
    quantity = models.IntegerField()
    in_stock = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} {self.category} {self.quantity} {self.in_stock}"
