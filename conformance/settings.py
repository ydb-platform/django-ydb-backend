"""
Settings for running Django's own database test suite against the YDB backend
(issue #72).

Django's bundled ``tests/runtests.py`` uses this module as the settings base and
adds its test apps on top. Only database configuration and a few globals are
needed here; everything else is supplied by ``runtests.py``.

Run via ``conformance/run.sh`` (which checks out a matching Django source tree),
for example::

    conformance/run.sh basic lookup queries
"""

# Two aliases share the single ``/local`` YDB database; the test runner gives
# each a distinct table-path prefix, so they do not collide. ``other`` is only
# exercised by Django's multi-database tests.
_BASE_DB = {
    "ENGINE": "ydb_backend.backend",
    "HOST": "localhost",
    "PORT": "2136",
    "DATABASE": "/local",
    "OPTIONS": {"credentials": None},
}

DATABASES = {
    "default": {**_BASE_DB, "NAME": "ydb_conformance"},
    "other": {**_BASE_DB, "NAME": "ydb_conformance_other"},
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
SECRET_KEY = "django-ydb-conformance"  # noqa: S105
# Match Django's own test settings (tests/test_sqlite.py): the bundled suite is
# written against USE_TZ = False, and many modules use naive datetimes.
USE_TZ = False

# Fast, deterministic password hashing for any auth-touching tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Django's TestCase isolates each test with a savepoint rollback. YDB has no
# savepoints, so the per-test rollback cannot undo just that test: it flags the
# whole connection as needing rollback and every test after the first fails with
# TransactionManagementError. Reporting transactions as unsupported makes
# Django's TestCase degrade to TransactionTestCase (flush-based isolation),
# which is the only way to run the bundled suite on YDB.
#
# This patch is scoped to the conformance harness process only; it does not
# change the shipped backend, whose savepoint limitation is a real, documented
# constraint (see the transaction contract, #36).
from ydb_backend.backend.features import DatabaseFeatures  # noqa: E402

DatabaseFeatures.supports_transactions = False
