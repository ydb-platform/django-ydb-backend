# Intentionally empty: this app's models exist only inside the on-disk
# migration fixtures under ``migrations_supported`` / ``migrations_unsupported``,
# which are loaded via MIGRATION_MODULES in tests/migration_executor/test_executor.py.
# Keeping models.py empty stops the test-database bootstrap from creating any
# tables for this app, leaving each executor test to migrate from a clean slate.
