from django.db import models


class Car(models.Model):
    MAKE_CHOICES = [
        ("Toyota", "Toyota"),
        ("Honda", "Honda"),
        ("BMW", "BMW"),
        ("Mercedes", "Mercedes"),
        ("Audi", "Audi"),
    ]

    COLOR_CHOICES = [
        ("Red", "Red"),
        ("Blue", "Blue"),
        ("Black", "Black"),
        ("White", "White"),
        ("Silver", "Silver"),
    ]

    id = models.PositiveIntegerField(primary_key=True)
    make = models.CharField(max_length=50, choices=MAKE_CHOICES)
    model = models.CharField(max_length=50)
    color = models.CharField(max_length=50, choices=COLOR_CHOICES)
    max_speed = models.IntegerField(help_text="Maximum speed in km/h")
    price = models.BigIntegerField()
    year = models.IntegerField()
    in_stock = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.id} "
            f"{self.make} "
            f"{self.model} "
            f"{self.year} "
            f"{self.color} "
            f"{self.max_speed} "
            f"{self.price} "
            f"{self.in_stock}"
        )
