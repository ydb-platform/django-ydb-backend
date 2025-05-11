from django.db import models
from ydb_backend.models.manager import YDBManager


class Book(models.Model):
    title = models.TextField()
    author = models.TextField(max_length=255)
    isbn = models.CharField(max_length=13, primary_key=True)
    price = models.IntegerField()

    def __str__(self):
        return (
            f"{self.title} "
            f"{self.author} "
            f"{self.isbn} "
            f"{self.price}"
        )


class Product(models.Model):
    sku = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    price = models.IntegerField()
    stock = models.IntegerField()

    def __str__(self):
        return (
            f"{self.sku} "
            f"{self.name} "
            f"{self.category} "
            f"{self.price} "
            f"{self.stock}"
        )


class SimpleItem(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    category = models.CharField(max_length=30)
    quantity = models.IntegerField()
    in_stock = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.code} "
            f"{self.category} "
            f"{self.quantity} "
            f"{self.in_stock}"
        )


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
            f"{self.name} "
            f"{self.device_type} "
            f"{self.room} "
            f"{self.ip_address} "
            f"{self.mac_address} "
            f"{self.status}"
        )


class NFTToken(models.Model):
    contract_address = models.CharField(max_length=42)
    token_id = models.CharField(max_length=78, primary_key=True)
    owner = models.CharField(max_length=42)
    metadata_url = models.CharField(max_length=256)
    last_price = models.FloatField()

    objects = YDBManager()

    def __str__(self):
        return (
            f"{self.contract_address} "
            f"{self.token_id} "
            f"{self.owner} "
            f"{self.metadata_url} "
            f"{self.last_price}"
        )
