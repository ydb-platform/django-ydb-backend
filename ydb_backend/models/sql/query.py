from django.db.models.sql import InsertQuery


class UpsertQuery(InsertQuery):
    """An INSERT-shaped query compiled with YDB's ``UPSERT INTO`` statement.

    YDB ``UPSERT INTO`` is keyed on the primary key: existing rows have their
    listed columns overwritten and missing rows are inserted, in a single
    atomic statement. It reuses Django's insert machinery (``insert_values``)
    and is compiled by ``SQLUpsertCompiler``, which is resolved by name from
    the ``compiler`` attribute through the backend's ``compiler_module``.
    """

    compiler = "SQLUpsertCompiler"
