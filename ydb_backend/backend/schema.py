import logging
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timezone
from enum import Enum
from uuid import UUID

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.transaction import TransactionManagementError

logger = logging.getLogger("django.db.backends.schema")


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


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    """
    This class and its subclasses are responsible for emitting schema-changing
    statements to the databases - model creation/removal/alteration, field
    renaming, index fiddling, and so on.
    """

    # TODO: WITH (STORE = %(store_type)s)
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
        "ALTER TABLE %(table)s ADD INDEX %(name)s GLOBAL ON (%(column)s);"
    )
    sql_create_unique_index = (
        "ALTER TABLE %(table)s ADD INDEX %(name)s GLOBAL UNIQUE ON (%(column)s);"
    )
    sql_rename_table = "ALTER TABLE %(old_table)s RENAME TO %(new_table)s;"
    sql_create_column = "ALTER TABLE %(table)s ADD COLUMN %(column)s %(definition)s;"
    sql_alter_column = "ALTER TABLE %(table)s %(changes)s;"
    sql_update_with_default = (
        "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL;"
    )

    # Not supported in YDB
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

            for element in model._meta.unique_together:
                if field.column in element:
                    pk.add(field)

            column_sqls.append(f"{self.quote_name(field.column)} {definition}")

        pk = sorted(pk)

        sql = self.sql_create_table % {
            "table": self.quote_name(model._meta.db_table),
            "definition": ", ".join(
                str(attribute) for attribute in column_sqls if attribute
            ),
            "primary_key": ", ".join(self.quote_name(field.column) for field in pk),
        }

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

    # def _create_index_sql(
    #         self,
    #         model,
    #         *,
    #         fields=None,
    #         name=None,
    #         suffix="",
    #         using="",
    #         db_tablespace=None,
    #         col_suffixes=(),
    #         sql=None,
    #         opclasses=(),
    #         condition=None,
    #         include=None,
    #         expressions=None,
    # ):
    #     """
    #     Return the SQL statement to create the index for one or several fields
    #     or expressions. `sql` can be specified if the syntax differs from the
    #     standard (GIS indexes, ...).
    #     """
    #     fields = fields or []
    #     expressions = expressions or []
    #     name = name or ""
    #
    #     compiler = Query(model, alias_cols=False).get_compiler(
    #         connection=self.connection,
    #     )
    #     columns = [field.column for field in fields]
    #     sql_create_index = self.sql_create_index
    #     table = model._meta.db_table
    #
    #     return Statement(
    #         sql_create_index,
    #         table=Table(table, self.quote_name),
    #         name=self.quote_name(name),
    #         columns=(
    #             self._index_columns(table, columns, col_suffixes, opclasses)
    #             if columns
    #             else Expressions(table, expressions, compiler, self.quote_value)
    #         ),
    #     )
    #
    # def _delete_index_sql(self, model, name, sql=None):
    #     return Statement(
    #         self.sql_delete_index,
    #         table=Table(model._meta.db_table, self.quote_name),
    #         name=self.quote_name(name),
    #     )
    #
    # def alter_db_table(self, model, old_db_table, new_db_table):
    #     """
    #     Rename the table a model points to.
    #     """
    #     if old_db_table == new_db_table or (
    #             self.connection.features.ignores_table_name_case
    #             and old_db_table.lower() == new_db_table.lower()
    #     ):
    #         return
    #     self.execute(
    #         self.sql_rename_table
    #         % {
    #             "old_table": self.quote_name(old_db_table),
    #             "new_table": self.quote_name(new_db_table),
    #         }
    #     )
    #
    # def remove_field(self, model, field):
    #     """
    #     Remove a field from a model. Usually involves deleting a column,
    #     but for M2Ms may involve deleting a table.
    #     """
    #     if field.many_to_many and field.remote_field.through._meta.auto_created:
    #         return self.delete_model(field.remote_field.through)
    #     sql = self.sql_delete_column % {
    #         "table": self.quote_name(model._meta.db_table),
    #         "column": self.quote_name(field.column),
    #     }
    #     self.execute(sql)
