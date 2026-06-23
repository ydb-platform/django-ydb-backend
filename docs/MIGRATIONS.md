Migrations
===

YDB is a distributed database, so some schema operations that traditional
databases (PostgreSQL, MySQL) allow require a different approach or are not
available at all. The schema editor never *silently* ignores an unsupported
operation: depending on how dangerous it is, it either fails fast with
`NotSupportedError` or is skipped with a logged warning and the migration
proceeds.

## Schema operations at a glance

| Operation | Status | Notes |
|-----------|:------:|-------|
| `CREATE` / `DROP TABLE` | ✅ | |
| Add a nullable column | ✅ | |
| Add a NOT NULL column **with a default** | ✅ | The default is written into the DDL so YDB can backfill existing rows. |
| Add a NOT NULL column **without a default** | ❌ | Raises `NotSupportedError` — YDB cannot backfill. Add it as nullable or give it a default. |
| Drop a column | ✅ | |
| Rename a table | ✅ | |
| Relax a column from NOT NULL to nullable | ✅ | |
| Make a column NOT NULL after creation | ❌ | Skipped with a warning — YDB can only drop NOT NULL, not add it. |
| Change a column type | ❌ | Raises `NotSupportedError`. |
| Rename a column | ❌ | Raises `NotSupportedError`. |
| Change the primary key | ❌ | Raises `NotSupportedError`. |
| Add / drop a secondary index | ✅ | |
| Change a column default | ❌ | No-op at the database level. Harmless: Django applies field defaults in Python, so new rows still get the new default. |
| Table / column comments, stored procedures | ❌ | Not supported. |

## Constraints at a glance

**YDB does not enforce referential, unique, or check constraints.** The ORM
still accepts the declaration, and the migration runs to completion, but the
guarantee must be implemented in application logic.

| Constraint | Status | Notes |
|-----------|:------:|-------|
| Primary key | ✅ | Must be set at table creation and is immutable afterwards. |
| NOT NULL (at create) | ✅ | Enforced. |
| `unique` / `unique_together` | ❌ | Not enforced by YDB (unique secondary indexes are unreleased). The migration skips the constraint with a warning and the database accepts duplicates; enforce with `validate_unique()` if needed. |
| Nullable / partially-nullable unique | ❌ | Not supported. |
| `CHECK` (column and table) | ❌ | Not supported; the migration skips it with a warning. Enforce in `clean()` / validators if needed. |
| Foreign-key constraints | ❌ | Not created or introspected. |
| Multiple constraints / indexes on the same fields | ❌ | Not supported. |

## Indexes at a glance

| Index type | Status | Notes |
|-----------|:------:|-------|
| Secondary, non-unique (`db_index`, `Index`) | ✅ | Added at table creation or via `ADD INDEX ... GLOBAL`. |
| Unique index | ❌ | Secondary indexes are non-unique; unique indexes are unreleased in YDB. |
| Partial index (`Index(..., condition=...)`) | ❌ | Not supported. |
| Expression index | ❌ | Not supported. |
| Covering index (`Index(include=...)`) | ✅ | Emits a `COVER (...)` clause so the index can satisfy a query without reading the table. |
| Rename index | ✅ | |
| Introspect column ordering (ASC/DESC) | ❌ | Introspection always reports ascending order. |

## How unsupported operations behave

- **Raises `NotSupportedError`** for changes that would leave the table and the
  Django model out of sync and break queries: renaming a column, changing a
  column type, and changing the primary key. The migration fails fast instead
  of corrupting the schema.
- **Skipped with a warning** for operations that YDB cannot honour but that
  leave the table queryable: unique / check constraints, `unique_together`, and
  making a column NOT NULL after creation. The migration logs a warning and
  proceeds.

Because unenforceable operations are skipped rather than rejected,
`python manage.py migrate` for the standard Django apps (`contenttypes`,
`auth`, `admin`, `sessions`) runs to completion. **Uniqueness and check
guarantees are not enforced by the database** and must be implemented in
application logic.

## Limited ALTER TABLE

**Supported:**
- Add a nullable column (`ADD COLUMN`).
- Add a NOT NULL column **that has a default** — the default is written into the
  DDL (`ADD COLUMN ... NOT NULL DEFAULT <value>`) so YDB can backfill existing
  rows.
- Remove a column (`DROP COLUMN`).
- Rename the table.
- Add / drop a secondary index for a field (`db_index`).
- Relax a column from NOT NULL to nullable (`ALTER COLUMN ... DROP NOT NULL`).

**Raises `NotSupportedError`:**
- Add a NOT NULL column **without a default** — YDB cannot backfill existing
  rows. Add it as nullable, or give the field a default.
- Change a column type.
- Rename a column.
- Change the primary key.
- Workaround: create a new table with the required schema and copy the data.

**Skipped with a warning:**
- Making a column NOT NULL after creation (YDB can only drop NOT NULL; the
  column keeps its current nullability).
- Default-value changes (defaults are applied by Django, not stored in YDB).

## Relations and many-to-many

Relations are stored as plain scalar columns (`<name>_id`) typed from the
target's primary key; no `FOREIGN KEY`, `REFERENCES` or `ON DELETE` SQL is
emitted, and referential integrity is left to the application.

Auto-created many-to-many through tables are created and dropped together with
their model (just like Django's base schema editor), so `ManyToManyField`
add / list / remove works at the ORM level. Custom (`through=`) models are
created as ordinary tables.

## Primary keys

- The primary key must be specified when the table is created.
- It cannot be changed afterwards (raises `NotSupportedError`).

## Multi-table inheritance and primary-key-only models

**Not supported (raises `NotSupportedError`):** inserting a row whose only
column is an auto-increment (`Serial`) primary key. YDB has no
`INSERT ... DEFAULT VALUES`, rejects `NULL` for a `Serial` column, and the
database — not the client — generates the key, so there is no value to insert.

This affects two model shapes:

- **Multi-table inheritance** (`class Child(Parent)` with a concrete parent):
  saving a child first inserts the parent row, which is primary-key-only.
- **Primary-key-only models** (`class M(models.Model): pass`).

Use a single concrete model (or `abstract = True` base classes) and give every
model at least one non-primary-key field.

## Introspection and `inspectdb`

Introspection reflects what YDB actually exposes through `DESCRIBE`.

| Aspect | Status | Notes |
|--------|:------:|-------|
| Column nullability | ✅ | A column reported as `Optional<T>` is nullable; otherwise it is NOT NULL. |
| Indexes (columns, ascending order) | ✅ | Secondary indexes are non-unique. |
| Sequences | 🟡 | Reported only for an integer primary key. |
| Field-type mapping (`inspectdb`) | 🟡 | Lossy where several Django fields share one YDB type (for example `Utf8` is reported as `TextField`, and `Double` as `FloatField`). |
| Foreign keys | ❌ | Never reported, because YDB does not enforce them. |
| Check constraints | ❌ | Never reported. |
| Column default | ❌ | Not introspected. |
