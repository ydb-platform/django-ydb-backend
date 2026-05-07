from datetime import datetime
from datetime import timezone

from django.db.models import Q
from django.test import TransactionTestCase

from .models import EventRecord
from .models import Product
from .models import ProductReview
from .models import SmartHomeDevice


class TestUpdate(TransactionTestCase):
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

        Product.objects.filter(Q(category="Electronics") | Q(price__gt=900)).update(
            price=899
        )

        self.assertEqual(Product.objects.get(sku="P1001").price, 899)
        self.assertEqual(Product.objects.get(sku="P2002").price, 199)

    def test_single_update(self):
        Product.objects.create(
            sku="P3003",
            name="Smart Watch",
            category="Wearables",
            price=299,
            stock=30,
        )

        product = Product.objects.get(sku="P3003")
        product.stock = 25
        product.save(update_fields=["stock"])

        updated = Product.objects.get(sku="P3003")
        self.assertEqual(updated.stock, 25)

    def test_foreign_key_filter_uses_target_field_type(self):
        product = Product.objects.create(
            sku="P4004",
            name="Smart Lock",
            category="Security",
            price=499,
            stock=15,
        )
        ProductReview.objects.create(product=product, rating=5)

        reviews = ProductReview.objects.filter(product__in={product}).values_list(
            "product",
            "rating",
        )

        self.assertEqual(list(reviews), [(product.pk, 5)])

    def test_mass_update(self):
        SmartHomeDevice.objects.create(
            name="Smart Lamp",
            device_type="LIGHT",
            room="Living Room",
            ip_address="192.168.1.10",
            mac_address="00:1A:2B:3C:4D:5E",
            status=True
        )
        SmartHomeDevice.objects.create(
            name="Nest Thermostat",
            device_type="THERMOSTAT",
            room="Bedroom",
            ip_address="192.168.1.11",
            mac_address="00:1A:2B:3C:4D:5F",
            status=True
        )
        SmartHomeDevice.objects.create(
            name="Security Camera",
            device_type="SECURITY",
            room="Front Door",
            ip_address="192.168.1.12",
            mac_address="00:1A:2B:3C:4D:60",
            status=True
        )
        SmartHomeDevice.objects.create(
            name="Robot Vacuum Cleaner",
            device_type="APPLIANCE",
            room="Kitchen",
            ip_address="192.168.1.13",
            mac_address="00:1A:2B:3C:4D:61",
            status=True
        )
        SmartHomeDevice.objects.create(
            name="Smart Speaker",
            device_type="MULTI",
            room="Office",
            ip_address="192.168.1.14",
            mac_address="00:1A:2B:3C:4D:62",
            status=True
        )

        SmartHomeDevice.objects.all().update(status=False)

        home_devices_status_cnt = SmartHomeDevice.objects.filter(status=True).count()
        self.assertEqual(home_devices_status_cnt, 0)
        self.assertEqual(
            SmartHomeDevice.objects.get(ip_address="192.168.1.14").status,
            False
        )


class TestDateTimeFieldUpdate(TransactionTestCase):
    """Regression tests for issue #54: 'int' object has no attribute 'timestamp'."""

    databases = {"default"}

    def setUp(self):
        self.dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.obj = EventRecord.objects.create(name="initial", occurred_at=self.dt)

    def test_update_datetime_field_with_datetime_object(self):
        new_dt = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        EventRecord.objects.filter(pk=self.obj.pk).update(occurred_at=new_dt)
        updated = EventRecord.objects.get(pk=self.obj.pk)
        self.assertEqual(updated.occurred_at, new_dt.replace(tzinfo=None))

    def test_filter_by_month_does_not_crash(self):
        # Regression for issue #54: filter(field__month=N) generates
        # DateTime::GetMonth(col) = %s where %s is an integer, not a datetime.
        # _generate_params_for_update must not call .timestamp() on that int.
        qs = EventRecord.objects.filter(occurred_at__month=1)
        self.assertEqual(qs.count(), 1)

    def test_filter_by_day_does_not_crash(self):
        qs = EventRecord.objects.filter(occurred_at__day=1)
        self.assertEqual(qs.count(), 1)
