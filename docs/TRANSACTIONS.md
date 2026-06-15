Transactions
===

> See the [support contract](SUPPORT.md#transactions) for the at-a-glance
> support matrix. This page explains the behavior in detail.

The backend maps Django's transaction API onto YDB's interactive transactions.

## What is supported

- **`transaction.atomic()`** — the body runs in an interactive transaction.
  On a clean exit the transaction is committed; on an exception (or
  `transaction.set_rollback(True)`) it is rolled back.
- **Autocommit** — outside an `atomic()` block every statement is its own
  transaction (the default).
- The connection stays usable after a rolled-back transaction.
- Isolation level is `SERIALIZABLE` for interactive transactions.

`supports_transactions` is `True`.

## What is not supported

- **Savepoints** (`uses_savepoints = False`). YDB has no savepoints, so nested
  `atomic()` blocks are not independent: a nested block does not create a
  savepoint, and an exception caught *inside* a nested block marks the whole
  transaction for rollback — further queries then raise
  `TransactionManagementError` until the outer block ends. Let exceptions
  propagate to the outermost `atomic()` instead of catching them mid-transaction.

- **Django `TestCase`**. It relies on savepoints to isolate each test, so it
  does not work here. Use **`TransactionTestCase`** (with `databases =
  {"default"}`) for database tests.

- **DDL inside `atomic()`** (`can_rollback_ddl = False`). YDB cannot roll back
  schema changes, so running DDL inside an `atomic()` block raises
  `TransactionManagementError`. Migrations are applied non-atomically for the
  same reason.

## Retries and conflicts

YDB uses optimistic concurrency with `SERIALIZABLE` isolation, so transactions
that touch the same rows concurrently can conflict. The losing transaction is
aborted with a retryable error, surfaced as `django.db.OperationalError`
("Transaction locks invalidated").

- **Statements in autocommit** (outside `atomic()`) are retried automatically by
  the YDB driver on transient/retryable errors — a single statement is its own
  transaction and is safe to replay.
- **`atomic()` blocks are not retried automatically.** Neither the driver (it
  cannot replay a multi-statement interactive transaction) nor Django (which has
  no built-in transaction retry) retries them. Retrying is the application's
  responsibility: catch `OperationalError` and re-run the whole block.

```python
from django.db import OperationalError, transaction

for attempt in range(3):
    try:
        with transaction.atomic():
            ...  # reads and writes
        break
    except OperationalError:
        if attempt == 2:
            raise
```
