from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        # Nullable column: added without a default.
        migrations.AddField(
            model_name="author",
            name="bio",
            field=models.TextField(null=True),
        ),
        # NOT NULL column with a default: the default is materialised into the
        # ADD COLUMN DDL so YDB can backfill existing rows.
        migrations.AddField(
            model_name="author",
            name="score",
            field=models.IntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="author",
            index=models.Index(fields=["name"], name="me_author_name_idx"),
        ),
    ]
