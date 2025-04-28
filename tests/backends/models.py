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
            f"{self.id}"
            f"{self.is_man} "
            f"{self.about}"
            f"{self.age}"
        )


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.id}, {self.name}"


class KeyModel(models.Model):
    key_1 = models.CharField(max_length=255)
    key_2 = models.IntegerField()
    key_3 = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key_1}, {self.key_2}, {self.key_3}"


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

