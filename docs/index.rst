Django YDB Backend
==================

Django database backend for `YDB <https://ydb.tech/>`_ — distributed SQL database.

Features
--------

- Full Django ORM support for YDB
- Support for all standard Django field types
- Custom UPSERT operation via ``YDBManager``
- Migrations support with YDB-specific limitations
- Multiple authentication methods

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

   CONFIGURATIONS
   FIELDS
   MIGRATIONS
   OPERATIONS
   TRANSACTIONS


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
