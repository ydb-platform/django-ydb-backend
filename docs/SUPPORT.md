Compatibility and limitations
===

YDB is a distributed database and does not behave exactly like PostgreSQL or
MySQL. This page is the high-level overview — the support legend, the supported
versions, and the handful of limitations worth knowing before you build on the
backend. Per-topic detail lives in [Fields](FIELDS.md),
[Migrations](MIGRATIONS.md), [Operations](OPERATIONS.md),
[Transactions](TRANSACTIONS.md), and [Admin, Auth & contrib](CONTRIB.md).

## Support levels

The topic pages mark each feature with one of:

| Level | Meaning |
|-------|---------|
| ✅ **Supported** | Works as documented. Safe to rely on within the stated caveats. |
| 🟡 **Best-effort** | Works, but with a documented caveat (partial coverage, an edge case, reduced precision). Read the note first. |
| ❌ **Unsupported** | Does not work, or the database does not enforce it. The backend either raises a clear error or accepts an ORM declaration that YDB never guarantees. |

**Database-enforced guarantees are credited only when YDB itself enforces
them.** Foreign keys, uniqueness, and check constraints are *not* enforced by
YDB, so they are marked ❌ even though the ORM still accepts the declaration. You
can reimplement them in application code (`validate_unique()`, `clean()`,
validators), but that is the application's responsibility.

## Supported versions

| Component | Supported | Recommended |
|-----------|-----------|-------------|
| **Python** | 3.10 – 3.13 | 3.12 |
| **Django** | 4.2 – 6.0 | 5.2 LTS |
| **YDB** | 20+ | latest stable |
| **ydb-dbapi** | 0.1.8+ | 0.1.8+ |

## Limitations to know before you build

These follow from YDB's architecture. Design around them.

1. **No database-enforced foreign keys, uniqueness, or checks.** The ORM accepts
   the declaration and migrations run to completion, but YDB does not enforce
   referential integrity, `unique` / `unique_together`, or `CHECK` constraints.
   Enforce them in application code. See [Migrations](MIGRATIONS.md) and
   [Fields](FIELDS.md).

2. **No savepoints.** Nested `atomic()` blocks cannot roll back independently,
   and Django's `TestCase` does not work — write database tests with
   `TransactionTestCase`. See [Transactions](TRANSACTIONS.md).

3. **No insert into a primary-key-only table.** A row whose only column is an
   auto-increment primary key cannot be inserted, which rules out **multi-table
   inheritance** (concrete parents) and **primary-key-only models** — both raise
   `NotSupportedError`. Give every model at least one non-primary-key field, and
   use `abstract = True` base classes instead of concrete parents. See
   [Migrations](MIGRATIONS.md).

4. **No correlated subqueries.** A subquery that references the enclosing query
   (`OuterRef` inside `Exists` / `Subquery`, or `exclude()` across a multivalued
   relationship) is not supported; non-correlated subqueries such as
   `field__in=<queryset>` work. See [Operations](OPERATIONS.md).

5. **No unique secondary indexes.** Secondary indexes are non-unique, so unique
   indexes — and the uniqueness they would back — are not available. See
   [Migrations](MIGRATIONS.md).
