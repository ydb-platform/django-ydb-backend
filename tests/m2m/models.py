import uuid

from django.db import models


# --- Auto-created through, integer target PK ---
class IntTag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=100)
    tags = models.ManyToManyField(IntTag, related_name="articles")

    def __str__(self):
        return self.title


# --- Auto-created through, string target PK ---
class StrItem(models.Model):
    code = models.CharField(max_length=20, primary_key=True)

    def __str__(self):
        return self.code


class StrBox(models.Model):
    name = models.CharField(max_length=50)
    items = models.ManyToManyField(StrItem)

    def __str__(self):
        return self.name


# --- Auto-created through, UUID target PK ---
class UuidItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    label = models.CharField(max_length=50)

    def __str__(self):
        return self.label


class UuidBox(models.Model):
    name = models.CharField(max_length=50)
    items = models.ManyToManyField(UuidItem)

    def __str__(self):
        return self.name


# --- Auto-created through, big integer target PK ---
class BigItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    label = models.CharField(max_length=50)

    def __str__(self):
        return self.label


class BigBox(models.Model):
    name = models.CharField(max_length=50)
    items = models.ManyToManyField(BigItem)

    def __str__(self):
        return self.name


# --- Custom (user-defined) through model ---
class Club(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Member(models.Model):
    name = models.CharField(max_length=50)
    clubs = models.ManyToManyField(
        Club, through="Membership", related_name="members"
    )

    def __str__(self):
        return self.name


class Membership(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.member} in {self.club} as {self.role}"
