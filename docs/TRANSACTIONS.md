Transactions
===

The backend maps Django's transaction API onto YDB's interactive transactions.

## What is supported

- **`transaction.atomic()`** — the body runs in an interactive transaction.
  On a clean exit the transaction is committed; on an exception (or
  `transaction.set_rollback(True)`) it is rolled back.
- **Autocommit** — outside an `atomic()` block every statement is its own
  transaction (the default).
- The connection stays usable after a rolled-back transaction.
- The isolation level is `SERIALIZABLE` for interactive transactions.

## What is not supported

- **Savepoints.** YDB has no savepoints, so nested `atomic()` blocks are not
  independent: a nested block does not create a savepoint, and an exception
  caught *inside* a nested block marks the whole transaction for rollback —
  further queries then raise `TransactionManagementError` until the outer block
  ends. Let exceptions propagate to the outermost `atomic()` instead of catching
  them mid-transaction.

- **Django `TestCase`.** It relies on savepoints to isolate each test, so it
  does not work here. Use **`TransactionTestCase`** (with
  `databases = {"default"}`) for database tests; with `pytest-django`, mark
  database tests `@pytest.mark.django_db(transaction=True)`.

- **DDL inside `atomic()`.** YDB cannot roll back schema changes, so running DDL
  inside an `atomic()` block raises `TransactionManagementError`. Migrations are
  applied non-atomically for the same reason.

## Row locking (`select_for_update`)

YDB has no pessimistic row locks and no `SELECT ... FOR UPDATE` (YQL rejects the
syntax), so `QuerySet.select_for_update()` is a **no-op**: it runs as a plain
`SELECT` and neither locks nor raises (`has_select_for_update = False`, like
SQLite). You do not lose serialization safety, though — YDB uses optimistic
concurrency, so a read-modify-write inside `transaction.atomic()` already takes
optimistic locks on the rows it reads, and a conflicting concurrent write makes
the **commit** fail with `OperationalError` ("Transaction locks invalidated").
Re-run the block on conflict instead of locking up front — wrap it with the
retry helper:

```python
from django.db import transaction
from ydb_backend.retry import retry_ydb_errors

@retry_ydb_errors(idempotent=True)
def reserve_stock(product_id):
    with transaction.atomic():
        product = Product.objects.get(pk=product_id)  # optimistically locked
        product.stock -= 1
        product.save()
```

## Retries and conflicts

YDB uses optimistic concurrency with `SERIALIZABLE` isolation, so transactions
that touch the same rows concurrently can conflict. The losing transaction is
aborted with a retryable error, surfaced as `django.db.OperationalError`
("Transaction locks invalidated").

- **Statements in autocommit** (outside `atomic()`) are retried automatically by
  the YDB driver on transient / retryable errors — a single statement is its own
  transaction and is safe to replay.
- **`atomic()` blocks are not retried automatically.** Neither the driver (it
  cannot replay a multi-statement interactive transaction) nor Django (which has
  no built-in transaction retry) retries them. Retrying is the application's
  responsibility — use the [`ydb_backend.retry`](RETRIES.md) helper, which
  retries only YDB-retriable errors using the native SDK policy:

```python
from django.db import transaction
from ydb_backend.retry import retry_ydb_errors

@retry_ydb_errors(idempotent=True)  # the transaction re-reads before writing
def transfer():
    with transaction.atomic():
        ...  # reads and writes
```

See [Retries](RETRIES.md) for idempotency rules, tuning and the full API.
