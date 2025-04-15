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


class SmartHomeDevice(models.Model):
    DEVICE_TYPE_CHOICES = [
        ("LIGHT", "Light"),
        ("THERMOSTAT", "Thermostat"),
        ("SECURITY", "Security"),
        ("APPLIANCE", "Appliance"),
        ("MULTI", "Multi-functional device"),
    ]

    name = models.CharField(
        max_length=255,
    )
    device_type = models.CharField(
        max_length=100,
        choices=DEVICE_TYPE_CHOICES
    )
    room = models.CharField(
        max_length=100,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        primary_key=True,
    )
    mac_address = models.CharField(
        max_length=17,
        unique=True,
    )
    status = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return (
            f"{self.name} {self.device_type} {self.room} "
            f"{self.ip_address} {self.mac_address} {self.status}"
        )
