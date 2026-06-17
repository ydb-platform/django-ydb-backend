django-ydb-backend
===

[![codecov](https://codecov.io/gh/ydb-platform/django-ydb-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/ydb-platform/django-ydb-backend)

Django YDB Backend
Overview
This is a Django database backend for [YDB](https://ydb.tech/), a distributed SQL database system.
The backend allows Django applications to use YDB as their primary database while maintaining compatibility with Django's ORM layer.

## Key Features
- Django ORM support for CRUD, relations, and the standard contrib apps
- Compatible with Django migrations system (with YDB-specific adaptations)
- Supports most common field types and query operations
- Implements necessary Django database backend interfaces

## Support and compatibility

YDB is a distributed database and does not behave exactly like PostgreSQL or
MySQL. Before relying on a feature in production, check the **support contract**,
which is the single source of truth for what is supported, best-effort,
unsupported, or not yet evaluated:

➡️ **[docs/SUPPORT.md](docs/SUPPORT.md)** — version support and compatibility
matrices for fields, relations, constraints, indexes, transactions, migrations,
ORM features, introspection, Admin/Auth, and UPSERT.

Key things to know up front: YDB does **not** enforce foreign keys, uniqueness,
or check constraints at the database level (they are application
responsibilities), there are **no savepoints** (so Django's `TestCase` and
nested `atomic()` rollback do not work — use `TransactionTestCase`), and
**primary-key-only / multi-table-inheritance models cannot be inserted**.

## Underlying Technology

### DBAPI Layer.
This backend uses the official [YDB-DBAPI](https://github.com/ydb-platform/ydb-python-dbapi) interface. The SDK provides:
- Connection pooling
- Session management
- Native support for YDB's distributed transactions
- Efficient data type handling

### Supported YDB Features
**Table Operations**:
- CREATE/DROP/ALTER TABLE
- Secondary indexes (with some limitations)

**Data Types**:
- All primitive YDB types (Int32, Utf8, Bool, etc.)
- Optional types (NULL support)
- JSON support via JSONField

**Query Capabilities**:
- SELECT with WHERE, ORDER BY, LIMIT
- Basic aggregations (COUNT, SUM, etc.)
- INSERT/UPDATE/DELETE, and emulated UPSERT via `YDBManager`

For the exact, per-feature breakdown (including what is best-effort or
unsupported), see the [support contract](docs/SUPPORT.md).

**Requirements:**
- [Python](https://www.python.org/) >= 3.10
- [Django](https://docs.djangoproject.com/) 4.2 (legacy floor), 5.2 LTS (recommended), or 6.0
- [YDB-DBAPI](https://github.com/ydb-platform/ydb-python-dbapi) >= 0.1.8

See [docs/SUPPORT.md](docs/SUPPORT.md#version-support) for the supported version
matrix and the first non-beta target range.

Get started
---

```shell
$ pip install django-ydb-backend
```

Configurations
---

To set up your Django project to use a YDB backend, you only need to modify a few of Django's built-in configuration settings. This project does not require any additional custom configuration options.
(Summary: Just adjust standard Django settings for YDB—no extra YDB-specific configurations are needed.)

### DATABASES

- NAME (required): traditional Django databases use this as the database name.
- ENGINE (required): required, set to `ydb_backend.backend`.
- HOST (required): the hostname or IP address of the YDB server (e.g., "localhost").
- PORT (required): The gRPC port YDB is running on (default is 2136).
- DATABASE (required): The full path to your YDB database (e.g., "/local" for local testing or "/my_production_db").

 ```python
DATABASES = {
    "default": {
        "NAME": "ydb_db",
        "ENGINE": "ydb_backend.backend",
        "HOST": "localhost",
        "PORT": "2136",
        "DATABASE": "/local",
    }
}
 ```

Test
---

To run tests for this project:

```shell
$ git clone https://github.com/ydb-platform/django-ydb-backend.git
$ cd django-ydb-backend
# docker and docker compose are required.
$ docker compose up -d --wait
$ pip install poetry && poetry install
$ poetry run python tests/runtests.py
```