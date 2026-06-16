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


class AlarmModel(models.Model):
    desc = models.CharField(max_length=100)
    time = models.TimeField()

    def __str__(self):
        return f"{self.desc} {self.time}"


class TextRelatedModel(models.Model):
    char_field = models.CharField(max_length=255)
    text_field = models.TextField()

    def __str__(self):
        return (
            f"{self.char_field} "
            f"{self.text_field} "
        )


class BlogPost(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    content = models.TextField()
    tags = models.CharField(max_length=200, blank=True)
    views = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return (
            f"{self.title} "
            f"{self.content} "
            f"{self.tags} "
            f"{self.views} "
            f"{self.is_published} "
        )


class JSONModel(models.Model):
    data = models.JSONField()
    label = models.CharField(max_length=100, default="")

    def __str__(self):
        return f"{self.label}: {self.data}"


class NullableJSONModel(models.Model):
    data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return str(self.data)


class NullableFieldsModel(models.Model):
    char_field = models.CharField(max_length=100, null=True, blank=True)  # noqa: DJ001
    int_field = models.IntegerField(null=True)
    big_int_field = models.BigIntegerField(null=True)
    float_field = models.FloatField(null=True)
    bool_field = models.BooleanField(null=True)
    date_field = models.DateField(null=True)
    datetime_field = models.DateTimeField(null=True)
    text_field = models.TextField(null=True, blank=True)  # noqa: DJ001

    def __str__(self):
        return f"NullableFieldsModel({self.pk})"
