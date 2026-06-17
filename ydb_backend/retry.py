"""Retry helper that reuses the native YDB SDK retry policy.

Django never retries queries, and ``ydb-dbapi`` only retries autocommit
statements through its session pool — never the body of an open
``transaction.atomic()`` (a single statement inside an interactive transaction
cannot be replayed transparently; the whole transaction must restart). This
module fills that gap **without re-implementing any policy**: a failing call is
unwrapped back to its ``ydb.issues.*`` cause and handed to the SDK's own
``ydb.retry_operation_sync``, so the set of retriable errors, the
idempotency rules and the backoff all come straight from the SDK and track its
updates automatically.

The underlying ydb-dbapi connection holds a self-healing YDB driver + session
pool, so a retry usually just needs to re-run on a fresh session the pool routes
to a live node. Between attempts the connection is cleaned up with Django's own
``close_if_unusable_or_obsolete()`` (the same hygiene Django applies at request
boundaries): it health-checks only after a connection-affecting error and closes
only a genuinely dead connection — a pool that merely lost one node is kept.

Typical use is to wrap a whole transaction so an aborted/transient one is
replayed::

    from ydb_backend.retry import retry_ydb_errors

    @retry_ydb_errors(idempotent=True)
    def transfer():
        with transaction.atomic():
            ...

To observe retries (e.g. for metrics), set ``on_ydb_error_callback`` on a
``ydb.RetrySettings`` and pass it as ``retry_settings`` — the SDK calls it for
every YDB error it sees while retrying.
"""

import functools

import ydb
from django.db import Error as DjangoDatabaseError
from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS


def unwrap_ydb_error(exc):
    """Return the underlying ``ydb.issues.Error`` of a wrapped exception.

    The wrapping chain is ``django.db.*`` -> ``ydb_dbapi`` error (which keeps the
    original on ``original_error``) -> ``ydb.issues.*``; both the ``__cause__``
    links and the ``original_error`` attribute are followed. Returns ``None`` when
    there is no YDB cause.
    """
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ydb.Error):
            return current
        original = getattr(current, "original_error", None)
        if isinstance(original, ydb.Error):
            return original
        current = current.__cause__
    return None


def retry_ydb_operation(
    func,
    *,
    idempotent=False,
    retry_settings=None,
    using=DEFAULT_DB_ALIAS,
    on_error=None,
):
    """Call ``func`` and retry it under the native YDB retry policy.

    Retry classification and backoff are delegated to ``ydb.retry_operation_sync``
    by re-raising the unwrapped ``ydb.issues.*`` cause, so nothing here changes
    when the SDK updates its policy. A non-retriable error (or running out of
    retries) re-raises the original Django exception; an error with no YDB cause
    is never retried.

    ``idempotent`` allows retries for errors that are only safe to repeat (e.g.
    ``Undetermined``) — pass it for reads and for transactions that re-read before
    writing. It is honoured only when ``retry_settings`` is not supplied;
    otherwise set ``idempotent`` on the passed ``ydb.RetrySettings``.

    After each failed attempt the ``using`` connection is run through Django's
    ``close_if_unusable_or_obsolete()`` so a dead connection is dropped before the
    next attempt while a healthy pooled one is kept; pass ``using=None`` to skip
    this. ``on_error`` is called with the caught Django exception after that, for
    any extra handling.
    """
    settings = (
        retry_settings
        if retry_settings is not None
        else ydb.RetrySettings(idempotent=idempotent)
    )
    captured = None

    def callee():
        nonlocal captured
        try:
            return func()
        except DjangoDatabaseError as exc:
            captured = exc
            if using is not None:
                connections[using].close_if_unusable_or_obsolete()
            if on_error is not None:
                on_error(exc)
            ydb_error = unwrap_ydb_error(exc)
            if ydb_error is None:
                raise
            raise ydb_error from exc

    try:
        return ydb.retry_operation_sync(callee, settings)
    except ydb.Error:
        # Retries exhausted or the error was non-retriable: surface the original
        # Django exception type, not the unwrapped SDK error.
        if captured is not None:
            raise captured from captured.__cause__
        raise


def retry_ydb_errors(
    *, idempotent=False, retry_settings=None, using=DEFAULT_DB_ALIAS, on_error=None
):
    """Decorator form of :func:`retry_ydb_operation`."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_ydb_operation(
                lambda: func(*args, **kwargs),
                idempotent=idempotent,
                retry_settings=retry_settings,
                using=using,
                on_error=on_error,
            )

        return wrapper

    return decorator
