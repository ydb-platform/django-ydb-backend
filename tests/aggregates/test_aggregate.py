from django.db.models import Avg
from django.db.models import Count
from django.db.models import Max
from django.db.models import Min
from django.db.models import Q
from django.db.models import Sum
from django.test import TransactionTestCase

from .models import Car


class TestAggregates(TransactionTestCase):
    databases = {"default"}

    def test_min_max_aggregation(self):
        cars = [
            {
                "id": 1001,
                "make": "Toyota",
                "model": "Camry",
                "color": "Black",
                "max_speed": 210,
                "price": 25000,
                "year": 2022,
                "in_stock": True,
            },
            {
                "id": 42,
                "make": "Toyota",
                "model": "Corolla",
                "color": "White",
                "max_speed": 250,
                "price": 22000,
                "year": 2021,
                "in_stock": True,
            },
            {
                "id": 9999,
                "make": "Honda",
                "model": "Civic",
                "color": "Red",
                "max_speed": 240,
                "price": 23000,
                "year": 2022,
                "in_stock": False,
            },
            {
                "id": 32678,
                "make": "BMW",
                "model": "X5",
                "color": "Black",
                "max_speed": 300,
                "price": 65000,
                "year": 2023,
                "in_stock": True,
            },
            {
                "id": 55555,
                "make": "Mercedes",
                "model": "E-Class",
                "color": "Silver",
                "max_speed": 300,
                "price": 60000,
                "year": 2023,
                "in_stock": True,
            },
            {
                "id": 789,
                "make": "Audi",
                "model": "A4",
                "color": "Blue",
                "max_speed": 260,
                "price": 45000,
                "year": 2022,
                "in_stock": False,
            },
            {
                "id": 2147483647,
                "make": "Toyota",
                "model": "RAV4",
                "color": "Blue",
                "max_speed": 240,
                "price": 28000,
                "year": 2023,
                "in_stock": True,
            },
        ]

        for car in cars:
            Car.objects.create(**car)

        aggregated_data = (
            Car.objects.values("make")
            .annotate(
                make_min_price=Min("price"),
                make_max_price=Max("price"),
                make_min_speed=Min("max_speed"),
                make_max_speed=Max("max_speed"),
            )
        )

        results = {item["make"]: item for item in aggregated_data}

        toyota_stats = results["Toyota"]
        self.assertEqual(toyota_stats["make_min_price"], 22000)
        self.assertEqual(toyota_stats["make_max_price"], 28000)
        self.assertEqual(toyota_stats["make_min_speed"], 210)
        self.assertEqual(toyota_stats["make_max_speed"], 250)

        bmw_stats = results["BMW"]
        self.assertEqual(bmw_stats["make_min_price"], 65000)
        self.assertEqual(bmw_stats["make_max_price"], 65000)
        self.assertEqual(bmw_stats["make_min_speed"], 300)
        self.assertEqual(bmw_stats["make_max_speed"], 300)

    def test_aggregation_with_q_objects(self):
        cars = [
            {
                "id": 1024,
                "make": "Toyota",
                "model": "Highlander",
                "color": "Black",
                "max_speed": 200,
                "price": 38000,
                "year": 2023,
                "in_stock": True,
            },
            {
                "id": 2048,
                "make": "BMW",
                "model": "X3",
                "color": "Blue",
                "max_speed": 280,
                "price": 52000,
                "year": 2022,
                "in_stock": True,
            },
            {
                "id": 4096,
                "make": "Toyota",
                "model": "Prius",
                "color": "Green",
                "max_speed": 180,
                "price": 32000,
                "year": 2024,
                "in_stock": False,
            },
            {
                "id": 8192,
                "make": "Honda",
                "model": "Accord",
                "color": "Black",
                "max_speed": 220,
                "price": 35000,
                "year": 2023,
                "in_stock": True,
            },
            {
                "id": 16384,
                "make": "Toyota",
                "model": "Tacoma",
                "color": "Red",
                "max_speed": 190,
                "price": 42000,
                "year": 2022,
                "in_stock": True,
            },
            {
                "id": 32768,
                "make": "BMW",
                "model": "M5",
                "color": "Black",
                "max_speed": 320,
                "price": 95000,
                "year": 2024,
                "in_stock": True,
            },
            {
                "id": 65536,
                "make": "Honda",
                "model": "CR-V",
                "color": "White",
                "max_speed": 210,
                "price": 33000,
                "year": 2023,
                "in_stock": True,
            },
            {
                "id": 131072,
                "make": "Audi",
                "model": "Q5",
                "color": "Gray",
                "max_speed": 250,
                "price": 48000,
                "year": 2022,
                "in_stock": False,
            },
            {
                "id": 262144,
                "make": "Toyota",
                "model": "Sienna",
                "color": "Blue",
                "max_speed": 185,
                "price": 40000,
                "year": 2024,
                "in_stock": True,
            },
            {
                "id": 524288,
                "make": "Mercedes",
                "model": "C-Class",
                "color": "Silver",
                "max_speed": 270,
                "price": 58000,
                "year": 2023,
                "in_stock": True,
            }
        ]

        for car in cars:
            Car.objects.create(**car)

        aggregated_data = Car.objects.values("make").annotate(
            brand_avg_price=Avg("price"),
            brand_count=Count("id"),
            brand_avg_price_in_stock=Avg("price", filter=Q(in_stock=True)),
            brand_count_in_stock=Count("id", filter=Q(in_stock=True)),
            brand_avg_price_high_speed=Avg("price", filter=Q(max_speed__gt=220)),
            brand_min_price_black=Min("price", filter=Q(color="Black")),
        )

        results = {item["make"]: item for item in aggregated_data}

        toyota = results["Toyota"]
        self.assertAlmostEqual(
            toyota["brand_avg_price"],
            (40000 + 42000 + 32000 + 38000) / 4
        )
        self.assertEqual(toyota["brand_count"], 4)
        self.assertAlmostEqual(
            toyota["brand_avg_price_in_stock"],
            (40000 + 42000 + 38000) / 3
        )
        self.assertEqual(toyota["brand_count_in_stock"], 3)
        self.assertIsNone(toyota["brand_avg_price_high_speed"])
        self.assertEqual(toyota["brand_min_price_black"], 38000)

        bmw = results["BMW"]
        self.assertEqual(bmw["brand_avg_price"], (95000 + 52000) / 2)
        self.assertEqual(bmw["brand_avg_price_high_speed"], (95000 + 52000) / 2)
        self.assertEqual(bmw["brand_min_price_black"], 95000)

    def test_complex_aggregation_with_multiple_q(self):
        cars = [
            {
                "id": 1,
                "make": "Toyota",
                "model": "Camry",
                "color": "Black",
                "max_speed": 210,
                "price": 25000,
                "year": 2022,
                "in_stock": True
            },
            {
                "id": 2,
                "make": "Toyota",
                "model": "Land Cruiser",
                "color": "Black",
                "max_speed": 190,
                "price": 85000,
                "year": 2024,
                "in_stock": True
            },
            {
                "id": 3,
                "make": "Toyota",
                "model": "RAV4",
                "color": "Black",
                "max_speed": 200,
                "price": 32000,
                "year": 2023,
                "in_stock": False
            },
            {
                "id": 4,
                "make": "Toyota",
                "model": "Corolla",
                "color": "Black",
                "max_speed": 220,
                "price": 23000,
                "year": 2023,
                "in_stock": True
            },
            {
                "id": 5,
                "make": "Toyota",
                "model": "Highlander",
                "color": "Black",
                "max_speed": 205,
                "price": 42000,
                "year": 2024,
                "in_stock": True
            },
            {
                "id": 6,
                "make": "BMW",
                "model": "X5",
                "color": "Black",
                "max_speed": 280,
                "price": 65000,
                "year": 2023,
                "in_stock": True
            },
            {
                "id": 7,
                "make": "BMW",
                "model": "7 Series",
                "color": "Black",
                "max_speed": 300,
                "price": 115000,
                "year": 2024,
                "in_stock": True
            },
            {
                "id": 8,
                "make": "BMW",
                "model": "M5",
                "color": "Black",
                "max_speed": 320,
                "price": 105000,
                "year": 2024,
                "in_stock": False
            },
            {
                "id": 9,
                "make": "BMW",
                "model": "X3",
                "color": "Black",
                "max_speed": 260,
                "price": 58000,
                "year": 2023,
                "in_stock": True
            },
            {
                "id": 10,
                "make": "BMW",
                "model": "i4",
                "color": "Black",
                "max_speed": 240,
                "price": 67000,
                "year": 2024,
                "in_stock": True
            },
            {
                "id": 11,
                "make": "Toyota",
                "model": "Prius",
                "color": "White",
                "max_speed": 180,
                "price": 30000,
                "year": 2024,
                "in_stock": True
            },
            {
                "id": 12,
                "make": "BMW",
                "model": "i8",
                "color": "Blue",
                "max_speed": 290,
                "price": 147000,
                "year": 2023,
                "in_stock": False
            }
        ]

        for car in cars:
            Car.objects.create(**car)

        aggregated_data = (
            Car.objects
            .filter(Q(make="Toyota") | Q(make="BMW"))
            .values("make", "color")
            .annotate(
                color_count=Count("id"),
                color_avg_price=Avg("price"),
                color_min_year=Min("year"),
                color_max_speed_in_stock=Max("max_speed", filter=Q(in_stock=True)),
                color_count_expensive=Count("id", filter=Q(price__gt=30000))
            )
            .order_by("make", "color")
        )

        results = {
            (item["make"], item["color"]): item
            for item in aggregated_data
        }

        toyota_black = results[("Toyota", "Black")]
        self.assertEqual(toyota_black["color_count"], 5)
        self.assertEqual(
            toyota_black["color_avg_price"],
            (25000 + 85000 + 32000 + 23000 + 42000) / 5
        )
        self.assertEqual(toyota_black["color_min_year"], 2022)
        self.assertEqual(toyota_black["color_max_speed_in_stock"], 220)
        self.assertEqual(toyota_black["color_count_expensive"], 3)

        bmw_black = results[("BMW", "Black")]
        self.assertEqual(bmw_black["color_count"], 5)
        self.assertEqual(
            bmw_black["color_avg_price"],
            (65000 + 115000 + 105000 + 58000 + 67000) / 5
        )
        self.assertEqual(bmw_black["color_min_year"], 2023)
        self.assertEqual(bmw_black["color_max_speed_in_stock"], 300)
        self.assertEqual(bmw_black["color_count_expensive"], 5)

    def test_compiler_with_q_objects(self):
        cars = [
            {
                "id": 1,
                "make": "Porsche",
                "model": "911",
                "color": "Blue",
                "max_speed": 240,
                "price": 120000,
                "year": 2002,
                "in_stock": True,
            },
            {
                "id": 2,
                "make": "Lada",
                "model": "Granta",
                "color": "Blue",
                "max_speed": 320,
                "price": 25000,
                "year": 2023,
                "in_stock": True,
            },
            {
                "id": 3,
                "make": "BMW",
                "model": "X5",
                "color": "Blue",
                "max_speed": 300,
                "price": 80000,
                "year": 2023,
                "in_stock": False,
            },
            {
                "id": 4,
                "make": "Kia",
                "model": "Rio",
                "color": "Blue",
                "max_speed": 240,
                "price": 28000,
                "year": 2023,
                "in_stock": False,
            },
            {
                "id": 5,
                "make": "Toyota",
                "model": "Corolla",
                "color": "Blue",
                "max_speed": 290,
                "price": 30000,
                "year": 2023,
                "in_stock": True,
            }
        ]

        for car in cars:
            Car.objects.create(**car)

        queryset = Car.objects.values("make").annotate(
            total=Count("id"),
            active=Count("id", filter=Q(in_stock=True)),
            sum_expensive=Sum("price", filter=Q(price__gt=30000))
        )

        compiler = queryset.query.get_compiler(using="default")
        sql, params = compiler.as_sql()

        self.assertIn("SELECT", sql)
        self.assertIn("COUNT", sql)
        self.assertIn("SUM", sql)
        self.assertIn("CASE WHEN", sql)
