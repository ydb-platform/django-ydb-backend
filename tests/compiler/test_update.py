from django.db.models import F
from django.db.models import Q
from django.test import TestCase

from .models import Product


class TestUpdate(TestCase):
    databases = {"default"}

    def test_filtered_update(self):
        Product.objects.create(
            sku="P1001",
            name="Smartphone X",
            category="Electronics",
            price=999,
            stock=50,
        )
        Product.objects.create(
            sku="P2002",
            name="Wireless Headphones",
            category="Audio",
            price=199,
            stock=100,
        )
        Product.objects.create(
            sku="P3003", name="Smart Watch", category="Wearables", price=299, stock=30
        )

        Product.objects.filter(Q(category="Electronics") | Q(price__gt=900)).update(
            price=899
        )

        self.assertEqual(Product.objects.get(sku="P1001").price, 899)
        self.assertEqual(Product.objects.get(sku="P2002").price, 199)

    def test_mass_update(self):
        Product.objects.all().update(price=F("price") * 2)

        products = Product.objects.all()
        self.assertAlmostEqual(products.get(sku="P1001").price, 1798, places=2)
        self.assertAlmostEqual(products.get(sku="P2002").price, 398, places=2)

    def test_single_update(self):
        product = Product.objects.get(sku="P3003")
        product.stock = 25
        product.save(update_fields=["stock"])

        updated = Product.objects.get(sku="P3003")
        self.assertEqual(updated.stock, 25)
        self.assertEqual(updated.price, 598)
