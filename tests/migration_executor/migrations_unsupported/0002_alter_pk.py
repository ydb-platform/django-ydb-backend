from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    """Changing the primary key is unsupported and must fail loudly."""

    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="age",
            field=models.IntegerField(primary_key=True),
        ),
    ]
