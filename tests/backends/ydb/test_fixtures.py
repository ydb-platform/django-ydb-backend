import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TransactionTestCase

from ..models import SimpleModel


class FixturesTest(TransactionTestCase):
    databases = {"default"}

    def test_dumpdata_loaddata_round_trip(self):
        # dumpdata serializes the row, then loaddata restores it — the fixture
        # workflow used for seeding and test data.
        obj = SimpleModel.objects.create(name="fixture-me")

        buffer = io.StringIO()
        call_command(
            "dumpdata",
            "backends.SimpleModel",
            "--pks",
            str(obj.pk),
            format="json",
            stdout=buffer,
        )
        dumped = buffer.getvalue()
        self.assertIn("fixture-me", dumped)

        SimpleModel.objects.filter(pk=obj.pk).delete()
        self.assertFalse(SimpleModel.objects.filter(pk=obj.pk).exists())

        path = Path(tempfile.gettempdir()) / "ydb_fixture_round_trip.json"
        path.write_text(dumped)
        try:
            call_command("loaddata", str(path), verbosity=0)
        finally:
            path.unlink()

        self.assertTrue(
            SimpleModel.objects.filter(pk=obj.pk, name="fixture-me").exists()
        )
