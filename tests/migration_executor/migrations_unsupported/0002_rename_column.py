from django.db import migrations


class Migration(migrations.Migration):
    """Renaming a column corrupts the schema and must fail loudly."""

    dependencies = [("migration_executor", "0001_initial")]

    operations = [
        migrations.RenameField(
            model_name="author",
            old_name="name",
            new_name="title",
        ),
    ]
