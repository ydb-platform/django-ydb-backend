Migrations
===

YDB is a distributed database, so some schema operations that traditional
databases (PostgreSQL, MySQL) allow require a different approach or are not
available at all. The schema editor never *silently* ignores an unsupported
operation — depending on how dangerous it is, it either:

- **raises `NotSupportedError`** for changes that would leave the table and the
  Django model out of sync and break queries (renaming a column, changing a
  column type, changing the primary key) — the migration fails fast instead of
  corrupting the schema; or
- **skips the operation with a logged warning** for things YDB cannot honour but
  that leave the table queryable (unique / check constraints, `unique_together`,
  making a column NOT NULL after creation) — the migration proceeds.

Because unenforceable operations are skipped rather than rejected,
`python manage.py migrate` for the standard Django apps (`contenttypes`, `auth`,
`admin`, `sessions`) runs to completion — but **uniqueness and check guarantees
are not enforced by the database** and must live in application logic.

## Schema changes (ALTER TABLE)

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

The workaround for these is to create a new table with the required schema and
copy the data across.

**Skipped with a warning:**
- Making a column NOT NULL after creation (YDB can only drop NOT NULL, not add
  it; the column keeps its current nullability).
- Default-value changes (defaults are applied by Django, not stored in YDB), so
  new rows still get the new default.

## Constraints

The primary key (set at table creation, immutable afterwards) and NOT NULL at
creation time are the constraints YDB enforces. The rest are accepted by the ORM
and the migration runs, but the database does **not** enforce them:

- **`unique` / `unique_together`** — not enforced (unique secondary indexes are
  unreleased in YDB). The migration skips the constraint with a warning and the
  database accepts duplicates; enforce with `validate_unique()` if you need it.
- **`CHECK` constraints** (column and table) — not supported; skipped with a
  warning. Enforce in `clean()` / validators.
- **Foreign-key constraints** — never created or introspected.
- Multiple constraints / indexes on the same fields are not supported.

## Indexes

- **Secondary, non-unique indexes** (`db_index`, `Index`) — supported, created at
  table creation or via `ADD INDEX ... GLOBAL`. Renaming an index works.
- **Covering indexes** (`Index(include=...)`) — supported; emit a `COVER (...)`
  clause so the index can satisfy a query without reading the table.
- **Unique indexes** are not available (secondary indexes are non-unique; unique
  indexes are unreleased in YDB), and **partial** and **expression** indexes are
  unsupported.

## Relations and many-to-many

Relations are stored as plain scalar columns (`<name>_id`) typed from the
target's primary key; no `FOREIGN KEY`, `REFERENCES` or `ON DELETE` SQL is
emitted, and referential integrity is left to the application.

Auto-created many-to-many through tables are created and dropped together with
their model, so `ManyToManyField`
add / list / remove works at the ORM level. Custom (`through=`) models are
created as ordinary tables.

## Primary keys

The primary key must be specified when the table is created, and it cannot be
changed afterwards (changing it raises `NotSupportedError`).

## Multi-table inheritance and primary-key-only models

Inserting a row whose only column is an auto-increment (`Serial`) primary key is
**not supported** and raises `NotSupportedError`: YDB has no
`INSERT ... DEFAULT VALUES`, rejects `NULL` for a `Serial` column, and the
database — not the client — generates the key, so there is no value to insert.

This affects two model shapes:

- **Multi-table inheritance** (`class Child(Parent)` with a concrete parent):
  saving a child first inserts the parent row, which is primary-key-only.
- **Primary-key-only models** (`class M(models.Model): pass`).

Use a single concrete model (or `abstract = True` base classes) and give every
model at least one non-primary-key field.

## Introspection and `inspectdb`

Introspection reflects what YDB actually exposes through `DESCRIBE`:

- **Column nullability** is accurate — a column reported as `Optional<T>` is
  nullable, otherwise NOT NULL.
- **Indexes** are reported with their columns in ascending order; secondary
  indexes are non-unique.
- **Sequences** are reported only for an integer primary key.
- **`inspectdb`** field-type mapping is lossy where several Django fields share
  one YDB type (for example `Utf8` is reported as `TextField`, `Double` as
  `FloatField`).
- **Foreign keys**, **check constraints**, and **column defaults** are never
  reported, because YDB does not enforce or store them.
