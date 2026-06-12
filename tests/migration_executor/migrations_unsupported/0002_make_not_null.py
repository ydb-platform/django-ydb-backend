from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    """nullable -> NOT NULL cannot be enforced after creation; skipped with a
    warning so ``migrate`` keeps working."""

    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="age",
            field=models.IntegerField(null=False, default=0),
        ),
    ]
