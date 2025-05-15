from django.db import models


class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    id = models.AutoField(primary_key=True)
    is_man = models.BooleanField(null=True)
    about = models.TextField(blank=True, default="")
    age = models.PositiveBigIntegerField()

    def __str__(self):
        return (
            f"{self.first_name} "
            f"{self.last_name} "
            f"{self.id} "
            f"{self.is_man} "
            f"{self.about} "
            f"{self.age}"
        )


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)

    def __str__(self):
        return (
            f"{self.id}, "
            f"{self.name}"
        )


class KeyModel(models.Model):
    key_1 = models.CharField(max_length=255)
    key_2 = models.IntegerField()
    key_3 = models.CharField(max_length=255)

    def __str__(self):
        return (
            f"{self.key_1}, "
            f"{self.key_2}, "
            f"{self.key_3}"
        )


class Square(models.Model):
    root = models.IntegerField()
    square = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.root} ** 2 == {self.square}"


class SimpleModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.id}: {self.name}"


class OldNameModel(models.Model):
    id = models.AutoField(primary_key=True)
    old_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.id}: {self.old_name}"


class MyModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.id}: {self.name}"


class ModelWithIndexes(models.Model):
    id = models.IntegerField(primary_key=True)
    single_idx_field = models.CharField(max_length=256, db_index=True)
    single_idx_field_w_name = models.IntegerField()
    first_part_composite_idx_field = models.BigIntegerField()
    second_part_composite_idx_field = models.TextField()
    third_part_composite_idx_field = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    condition_field = models.BooleanField()
    non_idx_first_field = models.CharField(max_length=256)
    non_idx_second_field = models.TextField()

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "first_part_composite_idx_field",
                    "second_part_composite_idx_field",
                    "third_part_composite_idx_field"
                ],
                name="composite_idx_w_name"
            ),
            models.Index(
                fields=[
                    "first_part_composite_idx_field",
                    "second_part_composite_idx_field"
                ],
            ),
            models.Index(
                fields=["name"],
                condition=models.Q(condition_field=True),
                name="partial_idx"
            ),
            models.Index(
                fields=["single_idx_field_w_name"],
                name="single_idx_w_name"
            ),
        ]

    def __str__(self):
        return (
            f"{self.id}, "
            f"{self.single_idx_field}, "
            f"{self.first_part_composite_idx_field} "
            f"{self.second_part_composite_idx_field} "
            f"{self.third_part_composite_idx_field} "
            f"{self.condition_field} "
            f"{self.name} "
            f"{self.non_idx_first_field}"
            f"{self.non_idx_second_field}"
        )
