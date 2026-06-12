import logging
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timezone
from enum import Enum
from uuid import UUID

from django.db import NotSupportedError
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.ddl_references import Columns
from django.db.backends.ddl_references import Statement
from django.db.transaction import TransactionManagementError

logger = logging.getLogger("django_ydb_backend.ydb_backend.backend.schema")


def _quote_null() -> str:
    return "NULL"


def _quote_number(item) -> str:
    return f"'{item}'"


def _quote_date(item) -> str:
    return f"'{item.strftime('%Y-%m-%d')}'"


def _quote_time(item) -> str:
    return f"'{item.strftime('%H:%M:%S')}'"


def _quote_datetime(item) -> str:
    if item.tzinfo is None:
        return item.timestamp()
    item = item.astimezone(timezone.utc)
    if item.microsecond == 0:
        return f"'{item.strftime('%Y-%m-%d %H:%M:%S')}'"
    return f"'{item.strftime('%Y-%m-%d %H:%M:%S.%f')}'"


def _quote_string(item) -> str:
    return "'" + item.replace("'", "''") + "'"


def _quote_list(item) -> str:
    return f"[{', '.join(str(_quote_value(element)) for element in item)}]"


def _quote_enum(item) -> str:
    return _quote_value(item.value)


def _quote_uuid(item) -> str:
    return f"'{item}'"


def _quote_value(item):
    handlers = {
        type(None): _quote_null,
        int: _quote_number,
        float: _quote_number,
        date: _quote_date,
        time: _quote_time,
        datetime: _quote_datetime,
        str: _quote_string,
        list: _quote_list,
        Enum: _quote_enum,
        UUID: _quote_uuid,
    }

    for type_, handler in handlers.items():
        if isinstance(item, type_):
            return handler(item)

    raise ValueError("Unsupported type for quoting: " + str(type(item)))


def _default_literal(value) -> str:
    """
    Render ``value`` as a literal for an ``ADD COLUMN ... DEFAULT`` clause.

    YDB is strict about default literals: numbers and booleans must be
    unquoted (``DEFAULT 0``, ``DEFAULT true``), so the param-style quoting from
    :func:`_quote_value` (which wraps numbers in quotes) cannot be reused here.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Enum):
        return _default_literal(value.value)
    if isinstance(value, str):
        return _quote_string(value)
    error_message = (
        f"YDB cannot render a column default of type {type(value).__name__!r}."
    )
    raise NotSupportedError(error_message)


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    """
    This class and its subclasses are responsible for emitting schema-changing
    statements to the databases - model creation/removal/alteration, field
    renaming, index fiddling, and so on.
    """

    # TODO: WITH (STORE = %(store_type)s)
    # TODO: Need to able create index while we create the table
    sql_create_table = (
        "CREATE TABLE %(table)s (%(definition)s, PRIMARY KEY (%(primary_key)s));"
    )
    sql_delete_table = "DROP TABLE %(table)s;"
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s;"
    sql_delete_index = "ALTER TABLE %(table)s DROP INDEX %(name)s;"
    sql_rename_index = (
        "ALTER TABLE %(table)s RENAME INDEX %(old_name)s TO %(new_name)s;"
    )
    sql_create_index = (
        "ALTER TABLE %(table)s ADD INDEX %(name)s GLOBAL ON (%(columns)s)%(include)s;"
    )
    # YDB has no GLOBAL UNIQUE variant in ALTER TABLE ADD INDEX syntax.
    sql_create_unique_index = None
    sql_rename_table = "ALTER TABLE %(old_table)s RENAME TO %(new_table)s;"
    sql_create_column = "ALTER TABLE %(table)s ADD COLUMN %(column)s %(definition)s;"
    sql_alter_column = "ALTER TABLE %(table)s %(changes)s;"
    # YDB can relax NOT NULL to nullable, but cannot add NOT NULL afterwards.
    sql_alter_column_drop_not_null = (
        "ALTER TABLE %(table)s ALTER COLUMN %(column)s DROP NOT NULL;"
    )
    sql_update_with_default = (
        "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL;"
    )

    sql_check_constraint = None
    sql_unique_constraint = None
    sql_delete_check = None
    sql_create_check = None
    sql_create_unique = None
    sql_delete_unique = None
    sql_rename_column = None
    sql_create_fk = None
    sql_create_inline_fk = None
    sql_create_column_inline_fk = None
    sql_delete_fk = None
    sql_delete_procedure = None
    sql_alter_table_comment = None
    sql_alter_column_comment = None
    sql_constraint = None
    sql_delete_constraint = None
    sql_create_pk = None
    sql_delete_pk = None
    sql_retablespace_table = None
    sql_alter_column_type = None
    sql_alter_column_null = None
    sql_alter_column_not_null = None
    sql_alter_column_default = None
    sql_alter_column_no_default = None
    sql_alter_column_no_default_null = None

    def _index_include_sql(self, model, columns):
        if not columns or not self.connection.features.supports_covering_indexes:
            return ""
        return Statement(
            " COVER (%(columns)s)",
            columns=Columns(model._meta.db_table, columns, self.quote_name),
        )

    def prepare_default(self, value):
        """
        Only used for backends which have requires_literal_defaults feature
        """

    def quote_value(self, value):
        """
        Return a quoted version of the value so it's safe to use in an SQL
        string. This is not safe against injection from user code; it is
        intended only for use in making SQL scripts or preparing default values
        for particularly tricky backends (defaults are not user-defined, though,
        so this is safe).
        """
        return _quote_value(value)

    def execute(self, sql, params=()):
        """
        Execute the given SQL statement, with optional parameters.
        """
        # Don't perform the transactional DDL check if SQL is being collected
        # as it's not going to be executed anyway.
        if (
                not self.collect_sql
                and self.connection.in_atomic_block
                and not self.connection.features.can_rollback_ddl
        ):
            raise TransactionManagementError(
                "Executing DDL statements while in a transaction on databases "
                "that can't perform a rollback is prohibited."
            )
        # Account for non-string statement objects.
        sql = str(sql)
        # Log the command we're running, then run it
        logger.debug(
            "%s; (params %r)", sql, params, extra={"params": params, "sql": sql}
        )
        if self.collect_sql:
            ending = "" if sql.rstrip().endswith(";") else ";"
            if params is not None:
                self.collected_sql.append(
                    (sql % tuple(map(self.quote_value, params))) + ending
                )
            else:
                self.collected_sql.append(sql + ending)
        else:
            with self.connection.cursor() as cursor:
                cursor.execute_scheme(sql, params)

    def table_sql(self, model):
        """
        Take a model and return its table definition.
        """
        column_sqls = []
        params = []
        pk = set()

        for field in model._meta.local_fields:
            definition, extra_params = self.column_sql(model, field)

            if definition is None:
                continue

            for element in extra_params:
                if isinstance(element, list) and element[0] == "pk":
                    pk.add(element[1])
                else:
                    params.append(element)

            column_sqls.append(f"{self.quote_name(field.column)} {definition}")

            # Autoincrement SQL (for backends with post table definition
            # variant).
            if field.get_internal_type() in (
                    "AutoField",
                    "BigAutoField",
                    "SmallAutoField",
            ):
                autoinc_sql = self.connection.ops.autoinc_sql(
                    model._meta.db_table, field.column
                )
                if autoinc_sql:
                    self.deferred_sql.extend(autoinc_sql)

        pk = sorted(pk)

        sql = self.sql_create_table % {
            "table": self.quote_name(model._meta.db_table),
            "definition": ", ".join(
                str(attribute) for attribute in column_sqls if attribute
            ),
            "primary_key": ", ".join(self.quote_name(field.column) for field in pk),
        }

        if model._meta.db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(
                model._meta.db_tablespace
            )
            if tablespace_sql:
                sql += " " + tablespace_sql

        return sql, params

    def column_sql(self, model, field, include_default=False):
        """
        Return the column definition for a field. The field must already have
        had set_attributes_from_name() called.
        """
        db_params = field.db_parameters(connection=self.connection)
        sql = db_params["type"]
        params = []
        if sql is None:
            return None, None
        if field.null and "Optional" not in sql:
            sql = f"Optional<{sql}>"
        if not field.null:
            sql += " NOT NULL"
        if field.primary_key:
            params.append(["pk", field])
        return sql, params

    def add_field(self, model, field):
        """
        Create a field on a model. Usually involves adding a column
        """
        # Get the column's definition
        definition, params = self.column_sql(model, field, include_default=True)
        # It might not actually have a column behind it
        if definition is None:
            return
        if col_type_suffix := field.db_type_suffix(connection=self.connection):
            definition += f" {col_type_suffix}"

        # YDB rejects ``ADD COLUMN ... NOT NULL`` unless a DEFAULT backfills
        # existing rows, so the field default must be materialised into the DDL.
        # A NOT NULL column without a usable default cannot be added.
        if not field.null:
            default = self.effective_default(field)
            if default is None:
                error_message = (
                    f"YDB cannot add the NOT NULL column {field.column!r} to "
                    f"{model._meta.db_table!r} without a default value. Add it "
                    f"as a nullable column or give the field a default."
                )
                raise NotSupportedError(error_message)
            definition += f" DEFAULT {_default_literal(default)}"

        # Build the SQL and run it
        sql = self.sql_create_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
            "definition": definition,
        }

        self.execute(sql, params or None)
        # Add an index, if required
        self.deferred_sql.extend(self._field_indexes_sql(model, field))

    def remove_field(self, model, field):
        """
        Remove a field from a model.
        """
        sql = self.sql_delete_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
        }
        self.execute(sql)

    def alter_db_table(self, model, old_db_table, new_db_table):
        """
        Rename the table a model points to.
        """
        if old_db_table == new_db_table or (
                self.connection.features.ignores_table_name_case
                and old_db_table.lower() == new_db_table.lower()
        ):
            return
        self.execute(
            self.sql_rename_table
            % {
                "old_table": self.quote_name(old_db_table),
                "new_table": self.quote_name(new_db_table),
            }
        )

    def create_model(self, model):
        """
        Create a table and any accompanying indexes or unique constraints for
        the given `model`.
        """
        sql, params = self.table_sql(model)
        # Prevent using [] as params, in the case a literal '%' is used in the
        # definition.
        self.execute(sql, params or None)

        # Add any field index and index_together's (deferred as SQLite
        # _remake_table needs it).
        self.deferred_sql.extend(self._model_indexes_sql(model))

        # Auto-created M2M through tables are plain tables carrying two relation
        # columns; mirror Django's base schema editor and create them too.
        # Custom (user-defined) through models are created as ordinary models,
        # so they are skipped here.
        for field in model._meta.local_many_to_many:
            if field.remote_field.through._meta.auto_created:
                self.create_model(field.remote_field.through)

    def delete_model(self, model):
        """Delete a model from the database."""

        # Drop the auto-created M2M through tables before the model table.
        for field in model._meta.local_many_to_many:
            if field.remote_field.through._meta.auto_created:
                self.delete_model(field.remote_field.through)

        # Delete the table
        self.execute(
            self.sql_delete_table
            % {
                "table": self.quote_name(model._meta.db_table),
            }
        )
        # Remove all deferred statements referencing the deleted table.
        for sql in list(self.deferred_sql):
            if isinstance(sql, Statement) and sql.references_table(
                    model._meta.db_table
            ):
                self.deferred_sql.remove(sql)

    def add_constraint(self, model, constraint):
        """
        YDB enforces neither uniqueness nor check constraints.

        The constraint is skipped with a warning rather than created: a hard
        error would break ``migrate`` for stock Django apps (django.contrib.*
        ship unique constraints), while silently materialising it would imply
        an integrity guarantee YDB cannot provide. Enforce such invariants in
        application code.
        """
        logger.warning(
            "YDB does not support database constraints; skipping %s %r on %r. "
            "Enforce this constraint in application code.",
            type(constraint).__name__,
            getattr(constraint, "name", None),
            model._meta.db_table,
        )

    def remove_constraint(self, model, constraint):
        """
        No-op: constraints are never created on YDB (see ``add_constraint``),
        so there is nothing to drop. Kept for migration-executor compatibility.
        """

    def alter_field(self, model, old_field, new_field, strict=False):
        """
        Apply the parts of a field alteration YDB supports and surface the rest
        instead of emitting broken DDL.

        Changes that would corrupt the schema (column rename, type change,
        primary-key change) raise ``NotSupportedError`` because the model and
        table would diverge and queries break. Changes YDB cannot apply but
        that keep the table queryable (nullability, newly added uniqueness) are
        skipped with a warning so ``migrate`` of stock Django apps keeps
        working; uniqueness in particular is never enforced by YDB. Purely
        cosmetic changes (default, help_text, verbose_name, choices, ...) are
        no-ops, and a ``db_index`` change is applied as a secondary index.
        """
        old_db_params = old_field.db_parameters(connection=self.connection)
        new_db_params = new_field.db_parameters(connection=self.connection)
        db_table = model._meta.db_table

        if old_field.column != new_field.column:
            error_message = (
                f"YDB cannot rename column {old_field.column!r} to "
                f"{new_field.column!r} on {db_table!r}."
            )
            raise NotSupportedError(error_message)
        if (old_db_params["type"] or "") != (new_db_params["type"] or ""):
            error_message = (
                f"YDB cannot change the type of column {new_field.column!r} on "
                f"{db_table!r} ({old_db_params['type']} -> "
                f"{new_db_params['type']})."
            )
            raise NotSupportedError(error_message)
        if old_field.primary_key != new_field.primary_key:
            error_message = f"YDB cannot alter the primary key of {db_table!r}."
            raise NotSupportedError(error_message)

        if old_field.null != new_field.null:
            if new_field.null:
                # NOT NULL -> nullable is supported by dropping NOT NULL.
                self.execute(
                    self.sql_alter_column_drop_not_null
                    % {
                        "table": self.quote_name(db_table),
                        "column": self.quote_name(new_field.column),
                    }
                )
            else:
                # nullable -> NOT NULL cannot be enforced after creation.
                logger.warning(
                    "YDB cannot make column %r on %r NOT NULL after creation; "
                    "skipping.",
                    new_field.column,
                    db_table,
                )
        if new_field.unique and not old_field.unique:
            logger.warning(
                "YDB does not enforce uniqueness for column %r on %r; skipping. "
                "Enforce it in application code.",
                new_field.column,
                db_table,
            )

        # Adding or dropping a secondary index for the field is supported.
        if old_field.db_index and not new_field.db_index:
            for index_name in self._constraint_names(
                model, [old_field.column], index=True
            ):
                self.execute(self._delete_index_sql(model, index_name))
        elif new_field.db_index and not old_field.db_index:
            self.deferred_sql.extend(self._field_indexes_sql(model, new_field))

    def alter_db_table_comment(self, model, old_db_table_comment, new_db_table_comment):
        """
        Table comments are not supported in YDB
        Method exists solely for Django ORM compatibility
        """

    def remove_procedure(self, procedure_name, param_types=()):
        """
        Stored procedures not supported in YDB
        Method exists solely for Django ORM compatibility
        """

    def alter_unique_together(self, model, old_unique_together, new_unique_together):
        """
        YDB does not enforce uniqueness. A newly added ``unique_together`` is
        skipped with a warning (so ``migrate`` of apps such as
        django.contrib.contenttypes keeps working); clearing one is a no-op.
        """
        old = {tuple(fields) for fields in (old_unique_together or ())}
        new = {tuple(fields) for fields in (new_unique_together or ())}
        added = new - old
        if added:
            logger.warning(
                "YDB does not enforce unique_together %s on %r; skipping. "
                "Enforce uniqueness in application code.",
                sorted(added),
                model._meta.db_table,
            )

    def _alter_column_null_sql(self, model, old_field, new_field):
        """
        YDB does not support altering NULL/NOT NULL constraints after table creation
        NULL constraints must be specified during CREATE TABLE only
        Returns None as required by Django ORM compatibility
        """
