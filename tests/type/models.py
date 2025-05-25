from django.db import models
from django.utils import timezone


class SmallAutoIncModel(models.Model):
    small_id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return (
            f"{self.small_id} "
            f"{self.name}"
        )


class RegularAutoIncModel(models.Model):
    regular_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return (
            f"{self.regular_id} "
            f"{self.name}"
        )


class BigAutoIncModel(models.Model):
    big_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return (
            f"{self.big_id} "
            f"{self.name}"
        )


class IntegerFieldsModel(models.Model):
    int_field = models.IntegerField()
    big_int_field = models.BigIntegerField()
    small_int_field = models.SmallIntegerField()
    positive_int_field = models.PositiveIntegerField()
    positive_big_int_field = models.PositiveBigIntegerField()
    positive_small_int_field = models.PositiveSmallIntegerField()

    def __str__(self):
        return (
            f"{self.int_field} "
            f"{self.big_int_field} "
            f"{self.small_int_field} "
            f"{self.positive_int_field} "
            f"{self.positive_big_int_field} "
            f"{self.positive_small_int_field}"
        )


class FloatingPointModel(models.Model):
    float_field = models.FloatField()
    decimal_field = models.DecimalField(
        max_digits=22,
        decimal_places=9
    )

    def __str__(self):
        return (
            f"{self.float_field} "
            f"{self.decimal_field}"
        )


class TimeModel(models.Model):
    date_field = models.DateField()
    datetime_field = models.DateTimeField(default=timezone.now)
    duration_field = models.DurationField()

    def __str__(self):
        return (
            f"Date: {self.date_field} | "
            f"Datetime: {self.datetime_field} | "
            f"Duration: {self.duration_field}"
        )


class TextRelatedModel(models.Model):
    char_field = models.CharField(max_length=255)
    text_field = models.TextField()

    def __str__(self):
        return (
            f"{self.char_field} "
            f"{self.text_field} "
        )
