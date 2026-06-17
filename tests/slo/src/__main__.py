"""Entry point for the Django key-value SLO workload.

Subcommands:

* ``create``  — create the ``slo_kv`` table (if absent) and seed initial rows
* ``run``     — run the read/write workload and push OTLP metrics
* ``cleanup`` — drop the ``slo_kv`` table

Connection details come from ``YDB_ENDPOINT`` / ``YDB_DATABASE`` (see
settings.py). Run as ``python tests/slo/src <subcommand> [options]``.
"""

import argparse
import logging
import os
import sys

logger = logging.getLogger("slo")

# Scenario names for the argparse choices. The implementations live in jobs.py,
# which can only be imported after django.setup().
_SCENARIOS = ("kv", "query")


def _env_int(name, default):
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def build_parser():
    parser = argparse.ArgumentParser(description="Django YDB SLO workload")
    parser.add_argument("--debug", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--records",
        type=int,
        default=_env_int("SLO_RECORDS", 1000),
        help="Size of the key space (primary keys 1..records)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create and seed the table")
    create.add_argument("--batch-size", type=int, default=100)

    sub.add_parser("cleanup", help="Drop the table")

    run = sub.add_parser("run", help="Run the workload")
    run.add_argument(
        "--scenario",
        choices=sorted(_SCENARIOS),
        default=os.environ.get("SLO_SCENARIO", "kv"),
        help="kv: point get/upsert; query: range scan + transactional RMW",
    )
    run.add_argument(
        "--time",
        type=int,
        default=_env_int("WORKLOAD_DURATION", 600),
        help="Run duration in seconds",
    )
    run.add_argument("--scan-range", type=int, default=50, help="query: PK scan width")
    run.add_argument("--scan-limit", type=int, default=10, help="query: rows per scan")
    run.add_argument("--read-rps", type=int, default=1000)
    run.add_argument("--write-rps", type=int, default=100)
    run.add_argument("--read-threads", type=int, default=8)
    run.add_argument("--write-threads", type=int, default=4)
    run.add_argument(
        "--report-period", type=int, default=1000, help="Metrics push period [ms]"
    )
    run.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Max YDB retries per operation (bounds how long a worker can block)",
    )
    run.add_argument(
        "--request-timeout",
        type=float,
        default=3.0,
        help="Per-attempt request timeout in seconds",
    )
    run.add_argument(
        "--otlp-endpoint",
        type=str,
        default="",
        help="OTLP metrics endpoint; usually taken from OTEL_* env vars",
    )
    return parser


def cmd_create(args):
    from django.db import connection

    from slo_app.models import KeyValue

    table = KeyValue._meta.db_table
    if table not in connection.introspection.table_names():
        logger.info("Creating table %s", table)
        try:
            with connection.schema_editor() as editor:
                editor.create_model(KeyValue)
        except Exception:
            # A parallel (baseline) container may win the race — tolerate it.
            if table not in connection.introspection.table_names():
                raise
            logger.warning("Table %s already created concurrently", table)
    else:
        logger.info("Table %s already exists", table)

    _seed(KeyValue, args.records, args.batch_size)


def _seed(model, records, batch_size):
    from generator import make_row

    logger.info("Seeding %d rows (batch=%d)", records, batch_size)
    seeded = 0
    for start in range(1, records + 1, batch_size):
        rows = [make_row(k) for k in range(start, min(start + batch_size, records + 1))]
        model.objects.bulk_upsert(rows)
        seeded += len(rows)
    logger.info("Seeded %d rows", seeded)


def cmd_cleanup(args):
    from django.db import connection

    from slo_app.models import KeyValue

    table = KeyValue._meta.db_table
    if table in connection.introspection.table_names():
        logger.info("Dropping table %s", table)
        with connection.schema_editor() as editor:
            editor.delete_model(KeyValue)
    else:
        logger.info("Table %s does not exist; nothing to drop", table)


def cmd_run(args):
    from jobs import JobManager
    from metrics import create_metrics

    metrics = create_metrics(args.otlp_endpoint)
    logger.info(
        "Running workload: scenario=%s time=%ds records=%d read(rps=%d,threads=%d) "
        "write(rps=%d,threads=%d)",
        args.scenario,
        args.time,
        args.records,
        args.read_rps,
        args.read_threads,
        args.write_rps,
        args.write_threads,
    )
    try:
        JobManager(args, metrics).run()
    finally:
        metrics.shutdown()
    logger.info("Workload finished")


def main():
    args = build_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    import django

    django.setup()

    handlers = {"create": cmd_create, "run": cmd_run, "cleanup": cmd_cleanup}
    handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
