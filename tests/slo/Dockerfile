# syntax=docker/dockerfile:1
#
# SLO workload image for ydb-slo-action. Build from the repository root:
#
#   docker build -f tests/slo/Dockerfile -t django-ydb-slo:current .
#
# The action runs this image inside the YDB cluster network and injects
# YDB_ENDPOINT / YDB_DATABASE / WORKLOAD_* / OTEL_* env vars (see
# tests/slo/docker-entrypoint.sh and tests/slo/README.md). Any
# `workload_current_command` arguments are appended to the `run` subcommand.
#
# hdrhistogram is built from sdist, so gcc/libc6-dev are needed.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install the backend under test (pulls Django + ydb-dbapi).
COPY pyproject.toml README.md ./
COPY ydb_backend/ ydb_backend/
RUN pip install --no-cache-dir .

# 2. Workload-only dependencies.
COPY tests/slo/requirements.txt tests/slo/requirements.txt
RUN pip install --no-cache-dir -r tests/slo/requirements.txt

# 3. Workload source + entrypoint.
COPY tests/slo/src tests/slo/src
COPY tests/slo/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
