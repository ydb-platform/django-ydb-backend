from django.db import models


class BookStore(models.Model):
    title = models.CharField(max_length=256)
    author = models.CharField(max_length=256)
    description = models.CharField(max_length=1024)
    quantity = models.PositiveIntegerField(null=True)
    record_dttm = models.DateTimeField(auto_now_add=True)
    release_dt = models.DateField(null=True)
    price = models.PositiveIntegerField(null=True)
    limited_edition = models.BooleanField(default=False, null=True)

    def __str__(self):
        return (
            f"{self.title} "
            f"{self.author} "
            f"{self.description} "
            f"{self.record_dttm} "
            f"{self.price} "
            f"{self.quantity} "
            f"{self.release_dt} "
            f"{self.limited_edition}"
        )
