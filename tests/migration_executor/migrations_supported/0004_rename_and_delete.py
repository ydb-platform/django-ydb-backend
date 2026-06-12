from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("migration_executor", "0003_drops")]

    operations = [
        migrations.AlterModelTable(
            name="author",
            table="migration_executor_author_renamed",
        ),
        migrations.DeleteModel(name="Tag"),
    ]
