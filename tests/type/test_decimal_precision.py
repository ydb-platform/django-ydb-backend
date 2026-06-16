from decimal import Decimal

from django.test import TransactionTestCase

from .models import DecimalPrecisionModel


class DecimalPrecisionTest(TransactionTestCase):
    """DecimalField with precision/scale beyond Decimal(22, 9) (issue #82).

    The column type and the bound parameter type both derive from the field's
    max_digits/decimal_places, so values that do not fit Decimal(22, 9)
    round-trip and filter correctly. (Values stay within YDB's reliable Decimal
    precision of ~26 significant digits.)
    """

    databases = {"default"}

    # 22 integer digits (Decimal(22, 9) allows only 13).
    WIDE = Decimal("1234567890123456789012.34")
    # 15 fractional digits (Decimal(22, 9) allows only 9).
    HIGH_SCALE = Decimal("12345.123456789012345")
    SMALL = Decimal("123.45")

    def test_create_and_read(self):
        obj = DecimalPrecisionModel.objects.create(
            wide=self.WIDE, high_scale=self.HIGH_SCALE, small=self.SMALL
        )
        fetched = DecimalPrecisionModel.objects.get(pk=obj.pk)
        self.assertEqual(fetched.wide, self.WIDE)
        self.assertEqual(fetched.high_scale, self.HIGH_SCALE)
        self.assertEqual(fetched.small, self.SMALL)

    def test_filter_exact(self):
        DecimalPrecisionModel.objects.create(
            wide=self.WIDE, high_scale=self.HIGH_SCALE, small=self.SMALL
        )
        DecimalPrecisionModel.objects.create(
            wide=Decimal("1.00"),
            high_scale=Decimal("0.000000000000001"),
            small=Decimal("0.01"),
        )
        # The lookup value is bound with the field's precision/scale.
        self.assertEqual(
            DecimalPrecisionModel.objects.filter(wide=self.WIDE).count(), 1
        )
        self.assertEqual(
            DecimalPrecisionModel.objects.filter(
                high_scale=self.HIGH_SCALE
            ).count(),
            1,
        )

    def test_update(self):
        obj = DecimalPrecisionModel.objects.create(
            wide=self.WIDE, high_scale=self.HIGH_SCALE, small=self.SMALL
        )
        new_wide = Decimal("999999999999999999999999.99")
        DecimalPrecisionModel.objects.filter(pk=obj.pk).update(wide=new_wide)
        obj.refresh_from_db()
        self.assertEqual(obj.wide, new_wide)

    def test_bulk_create(self):
        created = DecimalPrecisionModel.objects.bulk_create(
            [
                DecimalPrecisionModel(
                    wide=Decimal(f"{i}00000000000000000000.25"),
                    high_scale=Decimal("1.000000000000001"),
                    small=Decimal("9.99"),
                )
                for i in range(1, 4)
            ]
        )
        self.assertEqual(len(created), 3)
        self.assertEqual(DecimalPrecisionModel.objects.count(), 3)
