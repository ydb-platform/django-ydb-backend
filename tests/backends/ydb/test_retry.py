"""Tests for ydb_backend.retry.

These verify the retry decision is delegated to the native YDB SDK policy:
SDK-retriable issues (e.g. Aborted/Overloaded) are retried, non-retriable ones
(e.g. BadRequest) are not, and idempotency gating (Undetermined) is honoured —
without this module hard-coding any of those rules. No database is needed.
"""

import ydb
from django.db import OperationalError
from django.db import ProgrammingError
from django.test import SimpleTestCase
from ydb_backend.retry import retry_ydb_errors
from ydb_backend.retry import retry_ydb_operation
from ydb_backend.retry import unwrap_ydb_error


def _wrapped(django_exc_cls, ydb_issue):
    """Build a Django DB exception whose cause is a ``ydb.issues.*`` error,
    mirroring the ydb-dbapi -> Django wrapping chain."""
    exc = django_exc_cls("wrapped")
    exc.__cause__ = ydb_issue
    return exc


def _settings(max_retries, *, idempotent=False):
    # Zero the slow backoff slot so retried tests don't actually sleep; Aborted
    # additionally yields no sleep at all in the SDK.
    return ydb.RetrySettings(
        max_retries=max_retries,
        backoff_slot_duration=0.0,
        idempotent=idempotent,
    )


class UnwrapYdbErrorTests(SimpleTestCase):
    def test_follows_cause_chain(self):
        issue = ydb.issues.Aborted("tli")
        exc = _wrapped(OperationalError, issue)
        self.assertIs(unwrap_ydb_error(exc), issue)

    def test_follows_original_error_attribute(self):
        class FakeDBAPIError(Exception):
            pass

        issue = ydb.issues.Unavailable("down")
        err = FakeDBAPIError("x")
        err.original_error = issue
        self.assertIs(unwrap_ydb_error(err), issue)

    def test_returns_none_without_ydb_cause(self):
        self.assertIsNone(unwrap_ydb_error(ValueError("nope")))


class RetryOperationTests(SimpleTestCase):
    def test_retries_retriable_then_succeeds(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            if calls["n"] < 3:
                raise _wrapped(OperationalError, ydb.issues.Aborted("tli"))
            return "ok"

        result = retry_ydb_operation(op, retry_settings=_settings(5))
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_non_retriable_is_not_retried(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            raise _wrapped(ProgrammingError, ydb.issues.BadRequest("bad sql"))

        with self.assertRaises(ProgrammingError):
            retry_ydb_operation(op, retry_settings=_settings(5))
        self.assertEqual(calls["n"], 1)

    def test_exhaustion_raises_original_django_exception(self):
        def op():
            raise _wrapped(OperationalError, ydb.issues.Overloaded("busy"))

        with self.assertRaises(OperationalError):
            retry_ydb_operation(op, retry_settings=_settings(2))

    def test_undetermined_retried_only_when_idempotent(self):
        non_idem = {"n": 0}

        def op_non_idem():
            non_idem["n"] += 1
            raise _wrapped(OperationalError, ydb.issues.Undetermined("maybe"))

        with self.assertRaises(OperationalError):
            retry_ydb_operation(
                op_non_idem, retry_settings=_settings(3, idempotent=False)
            )
        self.assertEqual(non_idem["n"], 1)

        idem = {"n": 0}

        def op_idem():
            idem["n"] += 1
            raise _wrapped(OperationalError, ydb.issues.Undetermined("maybe"))

        with self.assertRaises(OperationalError):
            retry_ydb_operation(op_idem, retry_settings=_settings(2, idempotent=True))
        self.assertEqual(idem["n"], 3)  # first attempt + 2 retries

    def test_non_database_error_propagates_without_retry(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            raise ValueError("logic bug")

        with self.assertRaises(ValueError):
            retry_ydb_operation(op, retry_settings=_settings(5))
        self.assertEqual(calls["n"], 1)

    def test_on_error_called_per_failed_attempt(self):
        seen = []

        def op():
            raise _wrapped(OperationalError, ydb.issues.Aborted("tli"))

        with self.assertRaises(OperationalError):
            retry_ydb_operation(op, retry_settings=_settings(2), on_error=seen.append)
        self.assertEqual(len(seen), 3)  # first attempt + 2 retries

    def test_retriable_decorator(self):
        calls = {"n": 0}

        @retry_ydb_errors(retry_settings=_settings(5))
        def op():
            calls["n"] += 1
            if calls["n"] < 2:
                raise _wrapped(OperationalError, ydb.issues.Aborted("tli"))
            return 42

        self.assertEqual(op(), 42)
        self.assertEqual(calls["n"], 2)
