# django-ydb-backend

[![PyPI](https://img.shields.io/pypi/v/django-ydb-backend.svg)](https://pypi.org/project/django-ydb-backend/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/django-ydb-backend/)
![Django](https://img.shields.io/badge/Django-4.2%20%7C%205.2%20%7C%206.0-blue.svg)
[![Tests](https://github.com/ydb-platform/django-ydb-backend/actions/workflows/tests.yml/badge.svg)](https://github.com/ydb-platform/django-ydb-backend/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/ydb-platform/django-ydb-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/ydb-platform/django-ydb-backend)

A Django database backend for [YDB](https://ydb.tech/), a distributed SQL
database. It lets Django applications use YDB through the standard ORM — models,
migrations, queries, relations, and the contrib apps.

**[Documentation](https://ydb-platform.github.io/django-ydb-backend/)** ·
[PyPI](https://pypi.org/project/django-ydb-backend/) ·
[YDB](https://ydb.tech/) ·
[Issues](https://github.com/ydb-platform/django-ydb-backend/issues)

## Features

- Django ORM for CRUD, relations, and the standard contrib apps (admin, auth, sessions)
- Most built-in Django field types
- Migrations with YDB-specific adaptations
- Native, race-free `UPSERT` via `YDBManager`
- Multiple authentication methods (anonymous, static, access token, service account)

## Quick start

Install:

```shell
pip install django-ydb-backend
```

To develop against a local database, start YDB in Docker:

```shell
docker run -d --name ydb-local --hostname localhost \
  -p 2136:2136 -p 8765:8765 \
  -e YDB_USE_IN_MEMORY_PDISKS=true \
  ydbplatform/local-ydb:latest
```

This serves a ready-to-use database at `/local` on `localhost:2136` — the values
used below. Then point a Django database at YDB in `settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "ydb_backend.backend",
        "NAME": "ydb_db",
        "HOST": "localhost",
        "PORT": "2136",
        "DATABASE": "/local",
    }
}
```

Define a model, migrate, and query as usual:

```python
from django.db import models

class Product(models.Model):
    sku = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    price = models.IntegerField()
```

```shell
python manage.py makemigrations
python manage.py migrate
```

```python
Product.objects.create(sku="A1", name="Widget", price=9)
Product.objects.filter(price__lt=10)
```

See the [documentation](https://ydb-platform.github.io/django-ydb-backend/) for
configuration and authentication, fields, migrations, queries, transactions, and
UPSERT.

## Good to know

YDB is a distributed database and does not behave exactly like PostgreSQL or
MySQL. A few things to keep in mind:

- It does **not** enforce foreign keys, uniqueness, or check constraints —
  enforce these in application code.
- There are **no savepoints**, so Django's `TestCase` and nested `atomic()`
  rollback do not work — use `TransactionTestCase` for database tests.
- **Primary-key-only and multi-table-inheritance models cannot be inserted** —
  give every model at least one non-primary-key field.

The full list and the supported version matrix are in
[Compatibility and limitations](docs/SUPPORT.md).

## Requirements

- [Python](https://www.python.org/) >= 3.10
- [Django](https://www.djangoproject.com/) 4.2, 5.2 LTS, or 6.0
- [ydb-dbapi](https://github.com/ydb-platform/ydb-python-dbapi) >= 0.1.8

## Development

```shell
git clone https://github.com/ydb-platform/django-ydb-backend.git
cd django-ydb-backend
docker compose up -d --wait          # local YDB; requires docker + docker compose
pip install poetry && poetry install
poetry run python tests/runtests.py
```
