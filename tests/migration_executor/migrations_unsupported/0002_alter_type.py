from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    """Changing a column type is unsupported and must fail loudly."""

    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="age",
            field=models.TextField(null=True),
        ),
    ]
