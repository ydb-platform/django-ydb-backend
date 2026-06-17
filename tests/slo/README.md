# SLO workload (Django key-value)

SLO testing runs an application against a YDB cluster while a chaos monkey kills,
pauses, restarts and network-partitions nodes, then measures throughput,
availability and latency. This workload drives YDB **through the Django ORM and
`ydb_backend`** — the code path this repository ships — so the numbers reflect
the backend, not a raw SDK.

It plugs into [`ydb-platform/ydb-slo-action`](https://github.com/ydb-platform/ydb-slo-action);
see `.github/workflows/slo.yml`.

## The model

A single `KeyValue` model (`tests/slo/src/slo_app/models.py`): an explicit
integer primary key plus a small payload (`payload_str`, `payload_double`,
`payload_timestamp`). `create` seeds keys `1..records`, and the workload keeps
every key within that range so reads always hit an existing row.

Read and write jobs run in parallel at independent rates (`--read-rps` /
`--write-rps`, `--read-threads` / `--write-threads`); `--scenario` selects what
each does. Each logical operation is recorded once, tagged with the number of
retries the YDB SDK actually performed (see [Retries](#retries) below).

## Scenarios

Both scenarios use the same model and the same `read` / `write` operation types
(so the standard report metrics apply); they differ in what those operations do
and which backend code path they exercise.

### `kv` (default) — point key-value access

The classic key-value workload: single-row access by primary key, one round-trip
per operation.

| Op | ORM call | Statement | Backend path exercised |
|----|----------|-----------|------------------------|
| read | `KeyValue.objects.get(pk=key)` | `SELECT … WHERE id = $k` | SELECT compiler, point read |
| write | `KeyValue.objects.upsert(row)` | `UPSERT INTO slo_kv (…) VALUES (…)` | `YDBManager` / `UpsertQuery`, native UPSERT |

The write is a blind UPSERT — it never reads first, so outside of node failures
it needs no retries. This is the hot path with minimal per-op overhead.

### `query` — range scan + transactional read-modify-write

A heavier, more ORM-shaped mix that exercises what a real application hits beyond
plain key lookups.

| Op | ORM call | Statement | Backend path exercised |
|----|----------|-----------|------------------------|
| read | `KeyValue.objects.filter(id__gte=lo, id__lt=lo+scan_range).order_by("-payload_double")[:scan_limit]` | `SELECT … WHERE id >= $lo AND id < $hi ORDER BY payload_double DESC LIMIT n` | range predicate + `ORDER BY` + `LIMIT` compiler |
| write | `with transaction.atomic(): obj = …get(pk=key); obj.save(update_fields=…)` | `BEGIN; SELECT … WHERE id = $k; UPDATE slo_kv SET … WHERE id = $k; COMMIT` | interactive transaction (begin/commit) + UPDATE compiler |

The read is a bounded range scan with ordering and a top-N limit. The write is a
read-modify-write inside `transaction.atomic()`: an interactive transaction
spanning a SELECT and an UPDATE — several round-trips, and subject to YDB
optimistic-concurrency conflicts, so under load/chaos it retries where the `kv`
UPSERT does not. Tune the scan shape with `--scan-range` (PK window width) and
`--scan-limit` (rows returned).

## Metrics

Metrics are pushed via OTLP/HTTP to the Prometheus receiver the action provides.
Names follow the action contract:

```
sdk_operations_total{operation_type, operation_status, ref}
sdk_retry_attempts_total{operation_type, ref}
sdk_operation_latency_p50_seconds{operation_type, operation_status, ref}
sdk_operation_latency_p95_seconds{operation_type, operation_status, ref}
sdk_operation_latency_p99_seconds{operation_type, operation_status, ref}
```

Latency percentiles are computed client-side per push window (HdrHistogram) and
emitted as gauges. The `ref` label (current vs baseline) comes from
`WORKLOAD_REF`.

## CLI

Run as a directory module — `python tests/slo/src <subcommand>`:

| Subcommand | Purpose |
|------------|---------|
| `create`   | Create the `slo_kv` table (if absent) and seed `records` rows |
| `run`      | Run the read/write workload and push metrics |
| `cleanup`  | Drop the `slo_kv` table |

`run` flags: `--scenario {kv,query}`, `--time`, `--read-rps`, `--write-rps`,
`--read-threads`, `--write-threads`, `--report-period` (ms), `--max-retries`,
`--request-timeout` (s), `--scan-range`/`--scan-limit` (query scenario),
`--otlp-endpoint`. Key-space size is shared via `--records` / `SLO_RECORDS`.

The workflow runs both scenarios as a matrix (`django-kv`, `django-query`).

## Retries

Retries are handled where each kind needs them, and the workload counts the
**real** retries the YDB SDK performs (not just its own loop):

- **Autocommit** statements (point reads, UPSERTs, range scans) are retried by
  the YDB driver inside ydb-dbapi. The workload installs a `ydb.RetrySettings`
  on every connection (via the `connection_created` signal) whose
  `on_ydb_error_callback` increments a per-thread retry counter — so the
  driver's retries are observed.
- The **interactive transaction** (read-modify-write) is the one path the driver
  cannot replay, so it is wrapped with `@retry_ydb_errors` from
  `ydb_backend.retry` — the same way application code should guard its own
  transactions. It shares the same `RetrySettings`, so its retries are counted
  too.

`@retry_ydb_errors` delegates the retry/backoff decision to the native YDB SDK
policy (only YDB-retriable errors are retried) and applies Django's connection
hygiene between attempts. See [docs/RETRIES.md](../../docs/RETRIES.md).

The retry budget is bounded so a chaos-stuck worker fails fast instead of
hanging: `--max-retries` plus a per-attempt `--request-timeout` (installed on the
connection as `BaseRequestSettings().with_timeout(...)`) and a capped backoff —
worst-case ≈ `max_retries * (request_timeout + backoff)`.

## Connection

Connection details come from the environment the action injects, with local
fallbacks:

| Variable | Default | Used for |
|----------|---------|----------|
| `YDB_ENDPOINT` | `grpc://localhost:2136` | `HOST` / `PORT` |
| `YDB_DATABASE` | `/local` | `DATABASE` |
| `WORKLOAD_DURATION` | `600` | default `--time` |
| `WORKLOAD_REF` | `current` | `ref` metric label |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` / `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP push |

## Run locally

Against the repo's docker-compose YDB (`docker compose up -d --wait`):

```shell
docker build -f tests/slo/Dockerfile -t django-ydb-slo:local .

# create + 30s run, metrics disabled (no OTLP endpoint set)
docker run --rm --network host \
  -e YDB_ENDPOINT=grpc://localhost:2136 -e YDB_DATABASE=/local \
  django-ydb-slo:local sh -c \
  'python /app/tests/slo/src create && python /app/tests/slo/src run --time 30'
```
