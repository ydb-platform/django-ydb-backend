from django.db import models

from ydb_backend.models.manager import YDBManager


class KeyValue(models.Model):
    """Key-value row exercised by the SLO workload.

    The primary key is an explicit integer the workload controls, so reads can
    target keys that are known to exist. Writes go through ``YDBManager.upsert``
    (native YDB ``UPSERT INTO``), and reads through ``objects.get(pk=...)`` —
    both run entirely on the Django ORM + ydb_backend code path under test.
    """

    id = models.BigIntegerField(primary_key=True)
    payload_str = models.TextField()
    payload_double = models.FloatField()
    payload_timestamp = models.DateTimeField()

    objects = YDBManager()

    class Meta:
        db_table = "slo_kv"
