Django YDB Backend
==================

Django database backend for `YDB <https://ydb.tech/>`_ — distributed SQL database.

Features
--------

- Django ORM support for CRUD, relations, and the standard contrib apps
- Support for most standard Django field types (see the support matrix)
- Emulated UPSERT operation via ``YDBManager``
- Migrations support with YDB-specific limitations
- Multiple authentication methods

What is supported, best-effort, unsupported, or not yet evaluated is defined in
the :doc:`support contract <SUPPORT>` — the single source of truth, with
compatibility matrices for fields, relations, constraints, indexes,
transactions, migrations, ORM features, introspection, Admin/Auth, and UPSERT.

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install django-ydb-backend

Configuration
~~~~~~~~~~~~~

Add YDB to your Django settings:

.. code-block:: python

   DATABASES = {
       "default": {
           "NAME": "ydb_db",
           "ENGINE": "ydb_backend.backend",
           "HOST": "localhost",
           "PORT": "2136",
           "DATABASE": "/local",
       }
   }

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents

   SUPPORT
   CONFIGURATIONS
   FIELDS
   MIGRATIONS
   CONTRIB
   OPERATIONS
   TRANSACTIONS
   RETRIES


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
