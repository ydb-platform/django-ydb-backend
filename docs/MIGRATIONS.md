Migrations
===

Migrations are difficult and complex.

YDB, as a distributed OLTP/OLAP system, has a number of architectural limitations that significantly affect the migration process. 
Unlike traditional DBMS (PostgreSQL, MySQL), many YDB operations require a special approach or are not available at all.

## Limited ALTER TABLE

**Supported:**
- Add/remove columns (ADD COLUMN, DROP COLUMN).
- Rename the TABLE.

**Not supported:**
- Change the column type/name (ALTER COLUMN TYPE).
- NULL/NOT NULL change after creating the table.
- Bypass: It requires creating a new table with the required schema and copying the data.

## Uniqueness and Constraints
**Not supported**:
- UNIQUE constraints (even the sql_create_unique_index syntax in the code does not guarantee uniqueness).
- Foreign keys (FOREIGN KEY).
- Verification restrictions (CHECK).

**Solution:** Data integrity control falls on the application.

## Indexes
**Features:**
- Indexes are created via ADD INDEX ... GLOBAL (as in the code example) or are set when creating table.

## Primary Keys
**Strict requirements:**
- PK must be explicitly specified when creating the table (PRIMARY KEY (%(primary_key)s)).
- You cannot change the PK after creating the table.

## Comments and metadata
**Not supported:**
- Comments on tables/columns (sql_alter_table_comment = None).
- Stored procedures (sql_delete_procedure = None).
