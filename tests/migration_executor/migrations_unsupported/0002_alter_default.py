from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    """Defaults are applied by Django, not stored in YDB, so changing one is a
    harmless no-op that still applies cleanly."""

    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="age",
            field=models.IntegerField(null=True, default=7),
        ),
    ]
