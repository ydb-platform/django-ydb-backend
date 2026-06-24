Retries
===

> See [Transactions](TRANSACTIONS.md#retries-and-conflicts) for how conflicts
> arise. This page covers the retry helper shipped with the backend.

YDB is a distributed database: nodes restart, fail over and rebalance, and
optimistic `SERIALIZABLE` transactions abort on conflict. These are **expected,
retryable** conditions, and the YDB SDK already knows exactly which errors are
retryable and how to back off.

Two layers retry for you automatically:

- The **YDB driver / session pool** routes around dead nodes (endpoint
  discovery) and re-acquires sessions.
- **ydb-dbapi** retries **autocommit** statements (each is its own transaction
  and safe to replay) using the SDK policy.

What is **not** retried automatically is the body of an open
`transaction.atomic()`: a single statement inside an interactive transaction
cannot be replayed transparently — the whole transaction must restart, which
only your code can do. Django itself never retries queries. That gap is what
`ydb_backend.retry` fills.

## The helper

`ydb_backend.retry` provides a decorator and a function:

```python
from django.db import transaction
from ydb_backend.retry import retry_ydb_errors, retry_ydb_operation

# Decorator — guard a whole operation / transaction:
@retry_ydb_errors(idempotent=True)
def reserve_seat(event_id, user_id):
    with transaction.atomic():
        event = Event.objects.get(pk=event_id)
        event.free_seats -= 1
        event.save(update_fields=["free_seats"])
        Ticket.objects.create(event=event, user_id=user_id)

# Or wrap a callable inline:
def charge():
    with transaction.atomic():
        ...

retry_ydb_operation(charge, idempotent=True)
```

### How it works

A failing call is **unwrapped back to its `ydb.issues.*` cause** and handed to
the SDK's own `ydb.retry_operation_sync`. This means the set of retriable
errors, the idempotency rules and the backoff schedule all come **straight from
the SDK** — when the SDK updates its retry policy, this helper inherits it with
no changes here.

- A **non-retriable** error (e.g. a constraint or query error) and **running out
  of retries** re-raise the **original Django exception** (`OperationalError`,
  `IntegrityError`, …), not a raw SDK error.
- An error with **no YDB cause** is never retried.
- Between attempts the connection is cleaned up with Django's own
  `close_if_unusable_or_obsolete()`: a genuinely dead connection is dropped so
  the next attempt reconnects, while a healthy pooled one is kept (a single lost
  node does not force a full reconnect).

### Idempotency

Pass `idempotent=True` only when re-running the operation is safe. YDB
distinguishes errors where the transaction definitely did **not** apply (e.g.
`Aborted` — always retriable) from those where the outcome is **unknown** (e.g.
`Undetermined` — retried only when you declare the operation idempotent).

Safe to mark idempotent:

- reads;
- primary-key `UPSERT` (same key, same result);
- a read-modify-write transaction that **re-reads** inside `atomic()` before
  writing (replaying re-reads the current state).

Leave it `False` (the default) for operations that must not run twice on an
ambiguous outcome (e.g. a blind, non-keyed `INSERT`, or a counter increment that
is not derived from a fresh read).

### Tuning

By default the SDK policy is used (10 retries, exponential backoff). Override
with a `ydb.RetrySettings`:

```python
import ydb
from ydb_backend.retry import retry_ydb_errors

@retry_ydb_errors(retry_settings=ydb.RetrySettings(max_retries=5, idempotent=True))
def f():
    ...
```

When `retry_settings` is given it owns all knobs, so set `idempotent` on it
(the `idempotent=` argument is only used to build the default settings).

To stop a worker from blocking for a long time on a dead node, bound both the
retry count and each attempt's deadline. `max_retries`, `backoff_ceiling` and
`backoff_slot_duration` live on `ydb.RetrySettings`; the per-attempt timeout is a
`ydb.BaseRequestSettings().with_timeout(seconds)` installed on the connection
(`connection.connection.set_ydb_request_settings(...)`, e.g. from a
`connection_created` receiver). Worst-case time on one operation is then roughly
`max_retries * (request_timeout + backoff)`.

## API

`retry_ydb_operation(func, *, idempotent=False, retry_settings=None, using="default", on_error=None)`

- `func` — zero-argument callable to run (and retry).
- `idempotent` — allow retrying errors that are only safe to replay for
  idempotent operations. Used only when `retry_settings` is not supplied.
- `retry_settings` — a `ydb.RetrySettings`; overrides `idempotent` and the
  backoff.
- `using` — connection alias whose hygiene is managed between attempts
  (`close_if_unusable_or_obsolete()`); pass `None` to skip.
- `on_error(exc)` — optional hook called with the caught Django exception after
  each failed attempt (e.g. for logging or metrics).

`retry_ydb_errors(*, idempotent=False, retry_settings=None, using="default", on_error=None)`
is the decorator form with the same parameters.

## Observing retries

To count or log retries, set `on_ydb_error_callback` on a `ydb.RetrySettings` —
the SDK calls it for every YDB error it sees while retrying (in this helper and
in the driver's own retry of autocommit statements):

```python
import ydb
from django.db.backends.signals import connection_created

retries = 0

def _count(_err):
    global retries
    retries += 1

settings = ydb.RetrySettings(on_ydb_error_callback=_count)

# Count the driver's autocommit retries by installing the settings on every
# new connection:
def _install(sender, connection, **kwargs):
    inner = getattr(connection, "connection", None)
    if inner is not None:
        inner.set_ydb_retry_settings(settings)

connection_created.connect(_install)

# ...and pass the same settings to retry_ydb_errors/retry_ydb_operation to count
# transaction retries too.
```

## What not to wrap

- **Autocommit statements** are already retried by ydb-dbapi — wrapping a single
  `Model.objects.get(...)` outside a transaction is redundant (harmless, but
  unnecessary).
- **Operations with non-idempotent side effects** (sending email, charging a
  card) should not be retried unless those effects are guarded for replay.
