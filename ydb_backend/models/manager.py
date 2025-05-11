import logging

from django.db import models
from django.db import transaction
from django.db.models import QuerySet
from django.db.utils import DatabaseError
from django.db.utils import IntegrityError

logger = logging.getLogger("django_ydb_backend.models.manager")


class UpsertManager(models.Manager):
    def get_queryset(self):
        return UpsertQuerySet(self.model, using=self._db)

    def upsert(self, obj, conflict_target=None, update_fields=None):
        """
        UPSERT single object (model instance or dict)
        Returns the upserted model instance
        """
        if isinstance(obj, dict):
            obj = self.model(**obj)

        results = self.bulk_upsert(
            [obj],
            conflict_target=conflict_target,
            update_fields=update_fields
        )

        return results[0] if results else obj

    def bulk_upsert(self, objs, conflict_target=None, update_fields=None):
        """
        Bulk UPSERT objects (can mix instances and dicts)
        Returns list of upserted model instances
        """
        if not objs:
            return []

        # Convert all dicts to model instances
        objs = [
            self.model(**obj) if isinstance(obj, dict) else obj
            for obj in objs
        ]

        conflict_target = conflict_target or self._get_default_conflict_target()
        update_fields = (
                update_fields
                or self._get_default_update_fields(conflict_target)
        )

        # Try native UPSERT first
        native_upsert_supported = (
                hasattr(
                    self._db,
                    "features"
                ) and
                getattr(
                    self._db.features,
                    "can_return_upserted_objects",
                    False
                )
        )

        if native_upsert_supported:
            try:
                return self.get_queryset().bulk_upsert(
                    objs, conflict_target, update_fields
                )
            except DatabaseError as e:
                logger.debug("Database error during native UPSERT: %s", e)
            except NotImplementedError as e:
                logger.debug("UPSERT not implemented: %s", e)

        # Fallback to optimized emulated UPSERT
        return self._optimized_emulated_upsert(objs, conflict_target, update_fields)

    def _get_default_conflict_target(self):
        """Get default conflict target from model meta"""
        if self.model._meta.unique_together:
            return list(self.model._meta.unique_together[0])
        return [self.model._meta.pk.name]

    def _get_default_update_fields(self, conflict_target):
        """Get default fields to update (all except PK and conflict target)"""
        return [
            f.name for f in self.model._meta.fields
            if f.name not in conflict_target and not f.primary_key
        ]

    def _optimized_emulated_upsert(self, objs, conflict_target, update_fields):
        """
        Optimized emulated UPSERT that:
        1. Never creates duplicates
        2. Only updates changed fields
        3. Returns persisted objects
        """
        persisted_objs = []

        with transaction.atomic(using=self.db):
            for obj in objs:
                # Build filter for existing object
                filter_kwargs = {
                    field: getattr(obj, field)
                    for field in conflict_target
                }

                # Try to get existing object
                existing = self.filter(**filter_kwargs).first()

                if existing:
                    # UPDATE existing record if needed
                    needs_update = False
                    for field in update_fields:
                        new_value = getattr(obj, field)
                        if getattr(existing, field) != new_value:
                            setattr(existing, field, new_value)
                            needs_update = True

                    if needs_update:
                        existing.save(update_fields=update_fields)
                    persisted_objs.append(existing)
                else:
                    # INSERT new record
                    try:
                        obj.save(force_insert=True)
                        persisted_objs.append(obj)
                    except IntegrityError:
                        # Handle race condition
                        existing = self.filter(**filter_kwargs).first()
                        if not existing:
                            raise
                        persisted_objs.append(existing)

        return persisted_objs


class UpsertQuerySet(QuerySet):
    def bulk_upsert(self, objs, conflict_target, update_fields):
        """
        Native UPSERT implementation using compiler
        """
        # Convert dicts to model instances if needed
        objs = [
            self.model(**obj) if isinstance(obj, dict) else obj
            for obj in objs
        ]

        if not hasattr(self.query, "compiler"):
            raise NotImplementedError("This backend doesn't support native UPSERT")

        compiler = self.query.get_compiler(self.db)
        if not hasattr(compiler, "execute_upsert"):
            raise NotImplementedError("Compiler doesn't support execute_upsert")

        return compiler.execute_upsert(
            objs=objs,
            conflict_target=conflict_target,
            update_fields=update_fields,
            returning=True  # Ensure we get results back
        )
