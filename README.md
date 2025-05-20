django-ydb-backend
===

Django YDB Backend
Overview
This is a Django database backend for [YDB](https://ydb.tech/), a distributed SQL database system.
The backend allows Django applications to use YDB as their primary database while maintaining compatibility with Django's ORM layer.

## Key Features
- Full Django ORM support for basic CRUD operations
- Compatible with Django migrations system (with YDB-specific adaptations)
- Supports most common field types and query operations
- Implements necessary Django database backend interfaces

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
- INSERT/UPDATE/DELETE/UPSERT operations

**Requirements:**
- [Python](https://www.python.org/) >= 3.8
- [Django](https://docs.djangoproject.com/) >= 3.2.0
- [YDB-DBAPI](https://github.com/ydb-platform/ydb-python-dbapi) >= 0.1.8

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
- OPTIONS (optional): Additional settings for the YDB connection (e.g., credentials)

 ```python
DATABASES = {
    "default": {
        "NAME": "ydb_db",
        "ENGINE": "ydb_backend.backend",
        "HOST": "localhost",
        "PORT": "2136",
        "DATABASE": "/local",
        "OPTIONS": {
            "credentials": None,
        },
    }
}
 ```

Test
---

To run test for this project:

```shell
$ git clone https://github.com/ydb-platform/django-ydb-backend.git
$ cd django-ydb-backend
# docker and docker-compose are required.
$ docker-compose up
$ python tests/runtests.py
```