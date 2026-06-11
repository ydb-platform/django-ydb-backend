Migrations
===

YDB, as a distributed OLTP/OLAP system, has a number of architectural limitations that significantly affect the migration process. 
Unlike traditional DBMS (PostgreSQL, MySQL), many YDB operations require a special approach or are not available at all.

## How unsupported operations behave

The schema editor never *silently* ignores an unsupported operation. Depending
on how dangerous the operation is, it either fails fast or is skipped with a
logged warning:

- **Raises `NotSupportedError`** for changes that would leave the table and the
  Django model out of sync and break queries: renaming a column, changing a
  column type, and changing the primary key. The migration fails fast instead
  of corrupting the schema.
- **Skipped with a warning** for operations that YDB cannot honour but that
  leave the table queryable: unique/check constraints, `unique_together`, and
  nullability changes after table creation. These are logged (logger
  `django_ydb_backend.ydb_backend.backend.schema`) and the migration proceeds.

Because unenforceable operations are skipped rather than rejected,
`python manage.py migrate` for the standard Django apps (`contenttypes`,
`auth`, `admin`, `sessions`) runs to completion. **Uniqueness and check
guarantees are not enforced by the database** and must be implemented in
application logic.

## Limited ALTER TABLE

**Supported:**
- Add/remove columns (ADD COLUMN, DROP COLUMN).
- Rename the TABLE.
- Add/drop a secondary index for a field (`db_index`).

**Raises `NotSupportedError`:**
- Change the column type (ALTER COLUMN TYPE).
- Rename a column.
- Change the primary key.
- Workaround: create a new table with the required schema and copy the data.

**Skipped with a warning:**
- NULL/NOT NULL change after creating the table (the column keeps its original
  nullability).
- Default value changes are a no-op (defaults are applied by Django, not stored
  in YDB).

## Uniqueness and Constraints
**Not enforced (skipped with a warning):**
- UNIQUE constraints and `unique_together` (even the `sql_create_unique_index`
  syntax does not guarantee uniqueness in YDB).
- Verification restrictions (CHECK).

**Not supported:**
- Foreign keys (FOREIGN KEY) — no foreign-key constraints are created or
  introspected.

**Solution:** Data integrity control is assigned to the application logic.

## Indexes
**Features:**
- Indexes are created via ADD INDEX ... GLOBAL (as in the code example) or are set when creating table.
- Secondary indexes are non-unique.

## Primary Keys
**Strict requirements:**
- PK must be explicitly specified when creating the table (PRIMARY KEY (%(primary_key)s)).
- You cannot change the PK after creating the table (raises `NotSupportedError`).

## Comments and metadata
**Not supported:**
- Comments on tables/columns (sql_alter_table_comment = None).
- Stored procedures (sql_delete_procedure = None).

## Introspection and `inspectdb`

Introspection reflects what YDB actually exposes through `DESCRIBE`:

- **Nullability** is accurate: a column reported as `Optional<T>` is nullable,
  otherwise it is NOT NULL.
- **Sequences** are reported only for an integer primary key (the shape Django
  uses for auto fields); YDB does not expose `Serial` metadata directly.
- **Indexes** are reported with their columns and ascending order; secondary
  indexes are non-unique. Foreign keys and check constraints are never reported
  because YDB does not enforce them.
- **`inspectdb`** maps a YDB column type back to the closest Django field. The
  mapping is lossy where several Django fields share one YDB type (for example
  `Utf8` is reported as `TextField`, and `Double` as `FloatField`).
