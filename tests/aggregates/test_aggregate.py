from django.test import TestCase


class TestAggregates(TestCase):
    databases = {"default"}

    # @classmethod
    # def setUpTestData(cls):
    #     Car.objects.create(
    #         make="Toyota",
    #         model="Camry",
    #         color="Black",
    #         max_speed=210,
    #         price=25000,
    #         year=2022,
    #         in_stock=True,
    #     )
    #
    #     Car.objects.create(
    #         make="Toyota",
    #         model="Corolla",
    #         color="White",
    #         max_speed=190,
    #         price=22000,
    #         year=2021,
    #         in_stock=True,
    #     )
    #
    #     Car.objects.create(
    #         make="Honda",
    #         model="Civic",
    #         color="Red",
    #         max_speed=200,
    #         price=23000,
    #         year=2022,
    #         in_stock=False,
    #     )
    #
    #     Car.objects.create(
    #         make="BMW",
    #         model="X5",
    #         color="Black",
    #         max_speed=250,
    #         price=65000,
    #         year=2023,
    #         in_stock=True,
    #     )
    #
    #     Car.objects.create(
    #         make="Mercedes",
    #         model="E-Class",
    #         color="Silver",
    #         max_speed=240,
    #         price=60000,
    #         year=2023,
    #         in_stock=True,
    #     )
    #
    #     Car.objects.create(
    #         make="Audi",
    #         model="A4",
    #         color="Blue",
    #         max_speed=230,
    #         price=45000,
    #         year=2022,
    #         in_stock=False,
    #     )
    #
    #     Car.objects.create(
    #         make="Toyota",
    #         model="RAV4",
    #         color="Blue",
    #         max_speed=200,
    #         price=28000,
    #         year=2023,
    #         in_stock=True,
    #     )
    #
    # def test_min_max_aggregation(self):
    #     subquery = (
    #         Car.objects.filter(make=OuterRef("make"))
    #         .values("make")
    #         .annotate(
    #             min_price=Min("price"),
    #             max_price=Max("price"),
    #             min_speed=Min("max_speed"),
    #             max_speed=Max("max_speed"),
    #         )
    #     )
    #
    #     queryset = Car.objects.annotate(
    #         make_min_price=Subquery(subquery.values("min_price")),
    #         make_max_price=Subquery(subquery.values("max_price")),
    #         make_min_speed=Subquery(subquery.values("min_speed")),
    #         make_max_speed=Subquery(subquery.values("max_speed")),
    #     ).distinct("make")
    #
    #     results = {car.make: car for car in queryset}
    #
    #     toyota = results["Toyota"]
    #     self.assertEqual(toyota.make_min_price, 22000)
    #     self.assertEqual(toyota.make_max_price, 28000)
    #     self.assertEqual(toyota.make_min_speed, 190)
    #     self.assertEqual(toyota.make_max_speed, 210)
    #
    #     bmw = results["BMW"]
    #     self.assertEqual(bmw.make_min_price, 65000)
    #     self.assertEqual(bmw.make_max_price, 65000)
    #
    # def test_aggregation_with_q_objects(self):
    #     subquery = Car.objects.filter(make=OuterRef("make")).annotate(
    #         avg_price_all=Avg("price"),
    #         count_all=Count("id"),
    #         avg_price_in_stock=Avg("price", filter=Q(in_stock=True)),
    #         count_in_stock=Count("id", filter=Q(in_stock=True)),
    #         avg_price_high_speed=Avg("price", filter=Q(max_speed__gt=220)),
    #         min_price_black=Min("price", filter=Q(color="Black")),
    #     )
    #
    #     queryset = Car.objects.annotate(
    #         brand_avg_price=Subquery(subquery.values("avg_price_all")),
    #         brand_count=Subquery(subquery.values("count_all")),
    #         brand_avg_price_in_stock=Subquery(subquery.values("avg_price_in_stock")),
    #         brand_count_in_stock=Subquery(subquery.values("count_in_stock")),
    #         brand_avg_price_high_speed=Subquery(
    #             subquery.values("avg_price_high_speed")
    #         ),
    #         brand_min_price_black=Subquery(subquery.values("min_price_black")),
    #     ).distinct("make")
    #
    #     results = {car.make: car for car in queryset}
    #
    #     toyota = results["Toyota"]
    #     self.assertAlmostEqual(toyota.brand_avg_price, (25000 + 22000 + 28000) / 3)
    #     self.assertEqual(toyota.brand_count, 3)
    #     self.assertAlmostEqual(
    #         toyota.brand_avg_price_in_stock, (25000 + 22000 + 28000) / 3
    #     )
    #     self.assertEqual(toyota.brand_count_in_stock, 3)
    #     self.assertIsNone(
    #         toyota.brand_avg_price_high_speed
    #     self.assertEqual(toyota.brand_min_price_black, 25000)
    #
    #     bmw = results["BMW"]
    #     self.assertEqual(bmw.brand_avg_price, 65000)
    #     self.assertEqual(bmw.brand_avg_price_high_speed, 65000)
    #     self.assertEqual(bmw.brand_min_price_black, 65000)
    #
    # def test_complex_aggregation_with_multiple_q(self):
    #     subquery = Car.objects.filter(
    #         make=OuterRef("make"), color=OuterRef("color")
    #     ).annotate(
    #         count=Count("id"),
    #         avg_price=Avg("price"),
    #         min_year=Min("year"),
    #         max_speed=Max("max_speed", filter=Q(in_stock=True)),
    #         count_expensive=Count("id", filter=Q(price__gt=30000)),
    #     )
    #
    #     queryset = (
    #         Car.objects.annotate(
    #             color_count=Subquery(subquery.values("count")),
    #             color_avg_price=Subquery(subquery.values("avg_price")),
    #             color_min_year=Subquery(subquery.values("min_year")),
    #             color_max_speed_in_stock=Subquery(subquery.values("max_speed")),
    #             color_count_expensive=Subquery(subquery.values("count_expensive")),
    #         )
    #         .filter(Q(make="Toyota") | Q(make="BMW"))
    #         .order_by("make", "color")
    #     )
    #
    #     results = list(queryset)
    #
    #     toyota_black = next(
    #         c for c in results if c.make == "Toyota" and c.color == "Black"
    #     )
    #     self.assertEqual(toyota_black.color_count, 1)
    #     self.assertEqual(toyota_black.color_avg_price, 25000)
    #     self.assertEqual(toyota_black.color_min_year, 2022)
    #     self.assertEqual(toyota_black.color_max_speed_in_stock, 210)
    #     self.assertEqual(toyota_black.color_count_expensive, 0)
    #
    #     bmw_black = next(c for c in results if c.make == "BMW" and c.color == "Black")
    #     self.assertEqual(bmw_black.color_count, 1)
    #     self.assertEqual(bmw_black.color_avg_price, 65000)
    #     self.assertEqual(bmw_black.color_count_expensive, 1)
    #
    #
    # def test_compiler_with_q_objects(self):
    #     query = Query(Model)
    #     query.annotate(
    #         total=Count('id'),
    #         active=Count('id', filter=Q(in_stock=True)),
    #         sum_expensive=Sum('price', filter=Q(price__gt=30000))
    #     )
    #
    #     compiler = SQLAggregateCompiler(query, None, None)
    #     sql, params = compiler.as_sql()
    #
    #     self.assertIn('SELECT', sql)
    #     self.assertIn('COUNT', sql)
    #     self.assertIn('SUM', sql)
    #     self.assertIn('CASE WHEN', sql)
    #     self.assertIn('subquery', sql)
