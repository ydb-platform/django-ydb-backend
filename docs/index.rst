Django YDB Backend
==================

A Django database backend for `YDB <https://ydb.tech/>`_, a distributed SQL
database. It lets Django applications use YDB through the standard ORM —
models, migrations, queries, relations, and the contrib apps.

Features
--------

- Django ORM for CRUD, relations, and the standard contrib apps (admin, auth,
  sessions)
- Most built-in Django field types (see :doc:`Fields <FIELDS>`)
- Migrations with YDB-specific adaptations
- Native, race-free ``UPSERT`` via ``YDBManager``
- Multiple authentication methods

Quick start
-----------

Install
~~~~~~~

.. code-block:: bash

   pip install django-ydb-backend

Configure
~~~~~~~~~

Point a Django database at YDB in ``settings.py``:

.. code-block:: python

   DATABASES = {
       "default": {
           "ENGINE": "ydb_backend.backend",
           "NAME": "ydb_db",
           "HOST": "localhost",
           "PORT": "2136",
           "DATABASE": "/local",
       }
   }

See :doc:`Configuration <CONFIGURATIONS>` for the available authentication
methods.

Define a model
~~~~~~~~~~~~~~~

.. code-block:: python

   from django.db import models

   class Product(models.Model):
       sku = models.CharField(max_length=20, primary_key=True)
       name = models.CharField(max_length=100)
       price = models.IntegerField()

Give every model at least one non-primary-key field — YDB cannot insert a row
whose only column is an auto-generated primary key.

Migrate and query
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python manage.py makemigrations
   python manage.py migrate

.. code-block:: python

   Product.objects.create(sku="A1", name="Widget", price=9)
   Product.objects.filter(price__lt=10)
   Product.objects.get(sku="A1")

Before you go to production
---------------------------

YDB differs from PostgreSQL/MySQL in a few ways that affect application design:

- It does **not** enforce foreign keys, uniqueness, or check constraints —
  enforce these in application code.
- It has **no savepoints**: nested ``atomic()`` rollback and Django's
  ``TestCase`` do not work — use ``TransactionTestCase`` for database tests.
- **Primary-key-only and multi-table-inheritance models cannot be inserted.**

See :doc:`Compatibility and limitations <SUPPORT>` for the full list and the
supported version matrix.

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents

   CONFIGURATIONS
   FIELDS
   MIGRATIONS
   OPERATIONS
   TRANSACTIONS
   RETRIES
   CONTRIB
   SUPPORT

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
