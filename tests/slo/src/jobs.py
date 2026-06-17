"""Read / write / metrics jobs for the SLO workload.

Every operation runs through the Django ORM on top of ydb_backend. Retries are
handled where each kind actually needs them:

- **autocommit** statements (point reads, UPSERTs, range scans) are retried by
  the YDB driver itself (ydb-dbapi wraps them in the session pool's retry);
- the **interactive transaction** (read-modify-write) is the one path the driver
  cannot replay, so it is guarded with ``@retry_ydb_errors`` — exactly how
  application code should guard its own transactions.

Both retry layers share one ``ydb.RetrySettings`` whose ``on_ydb_error_callback``
counts every YDB error the SDK retries, so the metric reflects the *real* driver
retries (not just our own). The connection-level settings are installed on each
new connection via the ``connection_created`` signal.

Two scenarios are available (``--scenario``):

``kv`` (default) — point key-value access: ``get(pk)`` / native ``upsert``.
``query`` — primary-key range scan + ``ORDER BY``/``LIMIT`` reads, and a
transactional read-modify-write.
"""

import logging
import random
import threading
import time
from datetime import datetime
from datetime import timezone

import ydb
from django.db import connections
from django.db import transaction
from django.db.backends.signals import connection_created

from generator import make_row
from generator import random_string
from metrics import OP_TYPE_READ
from metrics import OP_TYPE_WRITE
from ratelimiter import SyncRateLimiter
from slo_app.models import KeyValue
from ydb_backend.retry import retry_ydb_errors

logger = logging.getLogger(__name__)

DEFAULT_CONN = "default"

# Per-thread count of YDB errors the SDK retried during the current operation,
# fed by RetrySettings.on_ydb_error_callback from both retry layers.
_local = threading.local()


def _count_ydb_retry(_err):
    _local.retries = getattr(_local, "retries", 0) + 1


# All workload operations are idempotent (point reads, key-keyed UPSERTs, range
# scans, and the RMW transaction that re-reads before writing), so Undetermined
# is retriable too. Shared by both retry layers; the callback does the counting.
# Backoff is capped so a worker can't sleep for tens of seconds between attempts;
# max_retries and the per-attempt timeout come from CLI args (configure_retries).
_RETRY = ydb.RetrySettings(
    idempotent=True,
    on_ydb_error_callback=_count_ydb_retry,
    backoff_ceiling=3,
    backoff_slot_duration=0.3,
)
# Per-attempt deadline so a single call can't block on a dead node; replaced by
# configure_retries() before the run.
_request_settings = ydb.BaseRequestSettings()


def configure_retries(args):
    """Bound the retry budget from CLI args.

    Worst-case time on one operation is about
    ``max_retries * (request_timeout + backoff)`` — kept well under a minute so a
    chaos-stuck worker fails fast and moves on instead of hanging.
    """
    global _request_settings
    _RETRY.max_retries = args.max_retries
    _RETRY.max_session_acquire_timeout = args.request_timeout
    _request_settings = ydb.BaseRequestSettings().with_timeout(args.request_timeout)


def _install_conn_settings(sender, connection, **kwargs):
    # Configure every new ydb-dbapi connection so the driver's autocommit retries
    # (and the transactional statements) use our bounded retry policy + per-attempt
    # timeout, and run our counting callback.
    inner = getattr(connection, "connection", None)
    if inner is None:
        return
    if hasattr(inner, "set_ydb_retry_settings"):
        inner.set_ydb_retry_settings(_RETRY)
    if hasattr(inner, "set_ydb_request_settings"):
        inner.set_ydb_request_settings(_request_settings)


connection_created.connect(_install_conn_settings)


# --- kv scenario: point access (autocommit — the driver retries these) ---------
def _kv_read(args):
    KeyValue.objects.get(pk=random.randint(1, args.records))


def _kv_write(args):
    KeyValue.objects.upsert(make_row(random.randint(1, args.records)))


# --- query scenario ------------------------------------------------------------
def _query_read(args):
    lo = random.randint(1, max(1, args.records - args.scan_range))
    # PK range scan, ordered by a non-key column, top-N — a different compiler
    # path (range predicate + ORDER BY + LIMIT) than the kv point lookup.
    rows = KeyValue.objects.filter(
        id__gte=lo, id__lt=lo + args.scan_range
    ).order_by("-payload_double")[: args.scan_limit]
    list(rows)  # force evaluation


# The interactive transaction is the one path the driver cannot retry for us, so
# guard it with @retry_ydb_errors — the same way application code should. The
# shared _RETRY settings make its retries count too.
@retry_ydb_errors(retry_settings=_RETRY)
def _query_write(args):
    key = random.randint(1, args.records)
    # SELECT the row, then UPDATE it inside one interactive transaction.
    with transaction.atomic():
        obj = KeyValue.objects.get(pk=key)
        obj.payload_double = random.random()
        obj.payload_str = random_string()
        obj.payload_timestamp = datetime.now(timezone.utc)
        obj.save(
            update_fields=["payload_double", "payload_str", "payload_timestamp"]
        )


SCENARIOS = {
    "kv": (_kv_read, _kv_write),
    "query": (_query_read, _query_write),
}


def _execute(metrics, op_type, operation):
    """Time one logical operation and record it once.

    Retries happen below us (driver for autocommit, ``@retry_ydb_errors`` for the
    transaction) and bump ``_local.retries`` through the callback. ``attempts`` is
    ``retries + 1`` on success (first try plus retries), or the number of failed
    attempts when the operation ultimately fails.
    """
    _local.retries = 0
    start_ts = metrics.start(op_type)
    error = None
    try:
        operation()
    except Exception as err:  # noqa: BLE001 - recorded; the loop keeps running
        error = err
    retries = getattr(_local, "retries", 0)
    attempts = max(retries + (0 if error else 1), 1)
    metrics.stop(op_type, start_ts, attempts=attempts, error=error)


class JobManager:
    def __init__(self, args, metrics):
        configure_retries(args)
        self.args = args
        self.metrics = metrics
        self._stop = threading.Event()
        self._read_op, self._write_op = SCENARIOS[args.scenario]

    def run(self):
        threads = []
        threads += self._start_op_threads(
            OP_TYPE_READ, self.args.read_threads, self.args.read_rps, self._read_op
        )
        threads += self._start_op_threads(
            OP_TYPE_WRITE, self.args.write_threads, self.args.write_rps, self._write_op
        )
        threads.append(self._start_metrics_thread())

        deadline = time.time() + self.args.time
        try:
            while time.time() < deadline and any(t.is_alive() for t in threads):
                time.sleep(0.5)
        finally:
            self._stop.set()
            for t in threads:
                t.join()

    def _start_op_threads(self, op_type, count, rps, operation):
        # The RPS budget is shared across all threads of this operation type.
        limiter = SyncRateLimiter.from_rps(rps)
        threads = []
        for i in range(count):
            t = threading.Thread(
                name=f"slo_{op_type}_{i}",
                target=self._op_loop,
                args=(op_type, limiter, operation),
            )
            t.start()
            threads.append(t)
        return threads

    def _op_loop(self, op_type, limiter, operation):
        try:
            while not self._stop.is_set():
                with limiter:
                    _execute(self.metrics, op_type, lambda: operation(self.args))
        finally:
            connections[DEFAULT_CONN].close()

    def _start_metrics_thread(self):
        period_s = max(0.1, self.args.report_period / 1000.0)
        t = threading.Thread(
            name="slo_metrics", target=self._metrics_loop, args=(period_s,)
        )
        t.start()
        return t

    def _metrics_loop(self, period_s):
        while not self._stop.is_set():
            time.sleep(period_s)
            try:
                self.metrics.push()
            except Exception:  # noqa: BLE001 - keep pushing despite a hiccup
                logger.exception("metrics push failed")
