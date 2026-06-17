#!/bin/sh
# Workload entrypoint used by ydb-slo-action.
#
# The action launches this image (for the current and, optionally, baseline
# workloads) and injects the connection + workload env vars. Schema prep runs
# first, then the timed workload. Anything passed after the script name comes
# from `workload_current_command` / `workload_baseline_command` and is appended
# to the `run` subcommand (e.g. --read-rps 2000 --write-rps 200).
set -e

DURATION="${WORKLOAD_DURATION:-600}"
SRC=/app/tests/slo/src

echo "[slo] create + seed..."
# Idempotent; a parallel baseline container may have prepared the table already.
python "$SRC" create || echo "[slo] create exited non-zero (treated as prepared)" >&2

echo "[slo] run (duration=${DURATION}s)..."
exec python "$SRC" run --time "$DURATION" "$@"
