from django.db.backends.base.schema import BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    sql_create_table = "CREATE TABLE %(table)s (%(definition)s) PRIMARY KEY (%(primary_key)s)"
    sql_delete_table = "DROP TABLE %(table)s"
    '''sql_alter_column =
    sql_alter_column_type =
    sql_alter_column_null =
    sql_alter_column_not_null =
    sql_alter_column_default =
    sql_alter_column_no_default =
    sql_alter_column_no_default_null = sql_alter_column_no_default
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s"
    sql_rename_column = # вроде не умеет
    sql_update_with_default =
    sql_unique_constraint =
    sql_check_constraint =
    sql_delete_constraint =
    sql_constraint =
    sql_pk_constraint =
    sql_create_check =
    sql_delete_check = sql_delete_constraint
    sql_create_unique =
    sql_delete_unique = sql_delete_constraint
    sql_create_fk =
    sql_create_inline_fk =
    sql_create_column_inline_fk =
    sql_delete_fk = sql_delete_constraint
    sql_create_index =
    sql_create_unique_index =
    sql_rename_index =
    sql_delete_index =
    sql_create_pk = # вроде тож не умеет
    sql_delete_pk = sql_delete_constraint
    sql_delete_procedure =
    sql_alter_table_comment =
    sql_alter_column_comment ='''

    def prepare_default(self, value):
        pass

    def quote_value(self, value):
        pass
