from django.db import NotSupportedError
from django.db import models
from django.db import router

from .sql.query import UpsertQuery


class YDBManager(models.Manager):
    """Default manager that adds native YDB ``UPSERT INTO`` to a model.

    Set ``objects = YDBManager()`` on a model and call ``upsert()`` /
    ``bulk_upsert()``. Rows are matched by primary key: an existing row has its
    listed columns overwritten and a missing row is inserted, in a single
    atomic statement (no read-modify-write, so no race window).
    """

    def upsert(self, obj, conflict_target=None, update_fields=None):
        """UPSERT a single model instance or dict; return the instance."""
        return self.bulk_upsert(
            [obj],
            conflict_target=conflict_target,
            update_fields=update_fields,
        )[0]

    def bulk_upsert(self, objs, conflict_target=None, update_fields=None):
        """UPSERT model instances and/or dicts; return the instances.

        ``conflict_target`` is accepted for API symmetry but must name the
        primary key (YDB UPSERT is PK-keyed); anything else raises
        ``NotSupportedError``. ``update_fields`` restricts which non-key columns
        are written (all concrete fields by default). Columns left out are
        preserved on existing rows; omitting a NOT NULL column without a default
        will fail when a brand-new row has to be inserted.
        """
        if not objs:
            return []

        objs = [
            self.model(**obj) if isinstance(obj, dict) else obj
            for obj in objs
        ]
        self._check_conflict_target(conflict_target)
        fields = self._upsert_fields(update_fields)

        query = UpsertQuery(self.model)
        query.insert_values(fields, objs)

        opts = self.model._meta
        auto_pk = isinstance(
            opts.pk,
            models.AutoField | models.SmallAutoField | models.BigAutoField,
        )
        using = self._db or router.db_for_write(self.model)
        compiler = query.get_compiler(using=using)
        rows = compiler.execute_sql(
            returning_fields=[opts.pk] if auto_pk else None
        )
        # Echo back database-generated keys for auto-pk models; for a supplied
        # primary key the value is already on the instance.
        if auto_pk and rows:
            for obj, row in zip(objs, rows, strict=False):
                setattr(obj, opts.pk.attname, row[0])
        return objs

    def _check_conflict_target(self, conflict_target):
        if conflict_target is None:
            return
        pk = self.model._meta.pk
        targets = (
            [conflict_target]
            if isinstance(conflict_target, str)
            else list(conflict_target)
        )
        if targets not in ([pk.name], [pk.attname]):
            msg = (
                "YDB UPSERT is keyed on the primary key; conflict_target "
                f"{conflict_target!r} is not supported. Use the primary key "
                f"({pk.name!r}) or omit conflict_target."
            )
            raise NotSupportedError(msg)

    def _upsert_fields(self, update_fields):
        opts = self.model._meta
        if update_fields is None:
            return list(opts.local_concrete_fields)

        wanted = set(update_fields)
        pk = opts.pk
        selected = [pk]
        selected.extend(
            f
            for f in opts.local_concrete_fields
            if f is not pk and (f.name in wanted or f.attname in wanted)
        )

        # YDB UPSERT requires every NOT NULL column to be present in the
        # statement, even for rows that already exist, so update_fields may
        # only drop nullable columns. Fail clearly instead of leaking YDB's
        # "missing not null column" error.
        selected_set = set(selected)
        missing = [
            f.name
            for f in opts.local_concrete_fields
            if f not in selected_set and not f.null
        ]
        if missing:
            msg = (
                f"update_fields omits NOT NULL column(s) {missing!r}, which "
                "YDB UPSERT requires. Include them, or make the fields nullable."
            )
            raise NotSupportedError(msg)
        return selected
