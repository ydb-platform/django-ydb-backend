from django.db.backends.base.features import BaseDatabaseFeatures


class DatabaseFeatures(BaseDatabaseFeatures):
    # An optional tuple indicating the minimum supported database version.
    minimum_database_version = (23,)
