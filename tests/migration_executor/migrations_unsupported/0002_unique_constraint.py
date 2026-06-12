from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    """YDB does not enforce uniqueness; the constraint is skipped with a
    warning rather than created."""

    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        migrations.AddConstraint(
            model_name="author",
            constraint=models.UniqueConstraint(
                fields=["name"], name="uq_author_name"
            ),
        ),
    ]
