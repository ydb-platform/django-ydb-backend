from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("migration_executor", "0002_columns_and_index")]

    operations = [
        migrations.RemoveIndex(
            model_name="author",
            name="me_author_name_idx",
        ),
        migrations.RemoveField(
            model_name="author",
            name="bio",
        ),
    ]
