#!/usr/bin/env bash
#
# Run Django's bundled database test suite against the YDB backend (issue #72).
#
# Checks out a Django source tree matching the installed Django version into
# .django-src/ (gitignored) and runs its tests/runtests.py with the YDB settings
# in conformance/settings.py. Pass through any runtests.py arguments, e.g.:
#
#   conformance/run.sh basic lookup queries
#   conformance/run.sh -v2 --keepdb lookup
#
# Requires a running local YDB (docker compose up -d --wait).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY="${PY:-$REPO_ROOT/.venv/bin/python}"
DJ_VERSION="$("$PY" -c 'import django; print(django.get_version())')"
SRC="$REPO_ROOT/.django-src"

if [ "$(cat "$SRC/.version" 2>/dev/null || true)" != "$DJ_VERSION" ]; then
    echo "Cloning Django $DJ_VERSION source into $SRC ..."
    rm -rf "$SRC"
    git clone --quiet --depth 1 --branch "$DJ_VERSION" \
        https://github.com/django/django.git "$SRC"
    echo "$DJ_VERSION" >"$SRC/.version"
fi

export PYTHONPATH="$REPO_ROOT"
export DJANGO_TEST_DB_SUFFIX="${DJANGO_TEST_DB_SUFFIX:-conformance}"

cd "$SRC/tests"
# Optionally measure the backend's coverage while exercising it against
# Django's own suite. --parallel-mode lets the concurrent groups each write a
# separate data file for the caller to `coverage combine`; the source/omit
# config (and repo-relative paths) come from pyproject.toml.
if [ -n "${CONFORMANCE_COVERAGE:-}" ]; then
    exec "$PY" -m coverage run --parallel-mode \
        --rcfile="$REPO_ROOT/pyproject.toml" \
        runtests.py --settings=conformance.settings "$@"
fi
exec "$PY" runtests.py --settings=conformance.settings "$@"
