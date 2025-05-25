from collections import namedtuple

from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.backends.base.introspection import FieldInfo as BaseFieldInfo
from django.db.backends.base.introspection import TableInfo as BaseTableInfo

FieldInfo = namedtuple("FieldInfo", BaseFieldInfo._fields)
TableInfo = namedtuple("TableInfo", BaseTableInfo._fields)


def _create_sequences_info(table_name, column_name):
    sequences = []
    for field in column_name:
        sequence_info = {
            "table_name": table_name,
            "column_name": field.name,
        }
        sequences.append(sequence_info)
    return sequences


def _create_table_desc_info(columns):
    sequences = []
    for field in columns:
        sequence_info = FieldInfo(
            name=field.name,
            type_code=str(field.type),
            display_size=None,  # TODO: fill attributes with values
            internal_size=None,
            precision=None,
            scale=None,
            null_ok=None,
            default=None,
            collation=None,
        )
        sequences.append(sequence_info)
    return sequences


def _create_table_info(table_scheme_entry):
    return TableInfo(
        name=table_scheme_entry.name,
        type="t",  # TODO: how to find view type?
    )


def _get_constraint_tuple(
    columns,
    is_primary_key,
    is_unique,
    foreign_key=None,
    is_check=False,
    is_index=True,
    _type=None,
):
    return {
        "columns": columns,
        "primary_key": is_primary_key,
        "unique": is_unique,  # TODO: for indexes define
        "foreign_key": foreign_key,
        "check": is_check,
        "index": is_index,
        "type": _type,
    }


class DatabaseIntrospection(BaseDatabaseIntrospection):
    """Encapsulate backends-specific introspection utilities."""

    data_types_reverse = {
        0: "AutoField",
        1: "BigAutoField",
        2: "BinaryField",
        3: "BooleanField",
        4: "CharField",
        5: "DateField",
        6: "DateTimeField",
        7: "DecimalField",
        8: "DurationField",
        9: "FileField",
        10: "FilePathField",
        11: "FloatField",
        12: "DoubleField",
        13: "IntegerField",
        14: "BigIntegerField",
        15: "IPAddressField",
        16: "GenericIPAddressField",
        17: "NullBooleanField",
        18: "PositiveIntegerField",
        19: "PositiveBigIntegerField",
        20: "PositiveSmallIntegerField",
        21: "SlugField",
        22: "SmallAutoField",
        23: "SmallIntegerField",
        24: "TextField",
        25: "UUIDField",
        26: "JSONField",
        27: "EnumField",
        28: "EmailField",
    }

    def get_field_type(self, data_type, description):
        """
        Hook for a database backends to use the cursor description to
        match a Django field type to a database column.

        For Oracle, the column data_type on its own is insufficient to
        distinguish between a FloatField and IntegerField, for example.
        """
        if data_type == "SmallAutoField":
            return "Int16"
        if data_type == "AutoField":
            return "Int32"
        if data_type == "BigAutoField":
            return "Int64"

        return self.connection.data_types[data_type]

    def identifier_converter(self, name):
        """
        Apply a conversion to the identifier for the purposes of comparison.
        The default identifier converter is for case sensitive comparison.
        """
        return name.lower()

    def table_names(self, cursor=None, include_views=False):
        """
        Return a list of names of all tables that exist in the database.
        Sort the returned table list by Python's default sorting. Do NOT use
        the database's ORDER BY here to avoid subtle differences in sorting
        order between databases.
        """
        return sorted(
            ti.name
            for ti in self.get_table_list(cursor)
            if include_views or ti.type == "t"
        )

    def get_table_list(self, cursor):
        """
        Return an unsorted list of TableInfo named tuples of all tables and
        views that exist in the database.
        """
        result = []
        table_names = self.connection.get_table_names()

        for table_name in table_names:
            table_scheme_entry = self.connection.get_describe(table_name)
            result.append(_create_table_info(table_scheme_entry))
        return result

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        table_scheme_entry = self.connection.get_describe(table_name)
        return _create_table_desc_info(table_scheme_entry.columns)

    def get_sequences(self, cursor, table_name, table_fields=()):
        """
        Return a list of introspected sequences for table_name. Each sequence
        is a dict: {'table': <table_name>, 'column': <column_name>}. An optional
        'name' key can be added if the backends supports named sequences.
        """
        table_scheme_entry = self.connection.get_describe(table_name)
        return _create_sequences_info(table_name, table_scheme_entry.columns)

    def get_relations(self, cursor, table_name):
        """
        YDB does not support foreign key constraints.
        For Django and third-party apps only - always returns empty dict.
        User applications must implement referential integrity in application logic.
        """
        return {}

    def get_primary_key_columns(self, cursor, table_name):
        """
        Return a list of primary key columns for the given table.
        """
        table_scheme_entry = self.connection.get_describe(table_name)
        return table_scheme_entry.primary_key

    def get_constraints(self, cursor, table_name):
        """
        Retrieve any constraints or keys (unique, pk, fk, check, index)
        across one or more columns.

        Return a dict mapping constraint names to their attributes,
        where attributes is a dict with keys:
        * columns: List of columns this covers
        * primary_key: True if primary key, False otherwise
        * unique: True if this is a unique constraint, False otherwise
        * foreign_key: (table, column) of target, or None
        * check: True if check constraint, False otherwise
        * index: True if index, False otherwise.
        * orders: The order (ASC/DESC) defined for the columns of indexes
        * type: The type of the index (btree, hash, etc.)

        Some backends may return special constraint names that don't exist
        if they don't name constraints of a certain type (e.g. SQLite)
        """
        constraints = {}
        table_scheme_entry = self.connection.get_describe(table_name)

        if table_scheme_entry.primary_key:
            constraints["primary_key"] = _get_constraint_tuple(
                columns=table_scheme_entry.primary_key,
                is_primary_key=True,
                is_unique=True,
            )

        for index in table_scheme_entry.indexes:
            index_name = index.name
            columns = index.index_columns
            constraints[index_name] = _get_constraint_tuple(
                columns=columns,
                is_primary_key=False,
                is_unique=None,
            )

        return constraints
