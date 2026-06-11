from collections import namedtuple

import ydb
from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.backends.base.introspection import FieldInfo as BaseFieldInfo
from django.db.backends.base.introspection import TableInfo as BaseTableInfo

FieldInfo = namedtuple("FieldInfo", BaseFieldInfo._fields)
TableInfo = namedtuple("TableInfo", BaseTableInfo._fields)

# YDB primitive type names that back Django auto-increment (Serial) primary
# keys. YDB does not expose "Serial" through describe() — a Serial column is
# reported as its underlying integer type — so an integer primary key is the
# only signal available for auto-increment detection.
_INTEGER_TYPE_NAMES = frozenset(
    {
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "Uint8",
        "Uint16",
        "Uint32",
        "Uint64",
    }
)


def _resolve_base_type(column_type):
    """
    Unwrap a YDB ``Optional<T>`` column type, returning ``(base_type,
    is_nullable)``. Non-optional columns are NOT NULL.
    """
    if isinstance(column_type, ydb.OptionalType):
        return column_type.item, True
    return column_type, False


def _ydb_type_name(base_type):
    """Stable string key for a YDB column base type, e.g. ``Int32``/``Decimal``."""
    if isinstance(base_type, ydb.DecimalType):
        return "Decimal"
    return getattr(base_type, "name", str(base_type))


def _create_table_desc_info(columns):
    fields = []
    for column in columns:
        base_type, is_nullable = _resolve_base_type(column.type)
        precision = scale = None
        if isinstance(base_type, ydb.DecimalType):
            precision = base_type.precision
            scale = base_type.scale
        fields.append(
            FieldInfo(
                name=column.name,
                type_code=_ydb_type_name(base_type),
                display_size=None,
                internal_size=None,
                precision=precision,
                scale=scale,
                null_ok=is_nullable,
                default=None,
                collation=None,
            )
        )
    return fields


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
    orders=None,
    _type=None,
):
    return {
        "columns": list(columns),
        "primary_key": is_primary_key,
        "unique": is_unique,
        "foreign_key": foreign_key,
        "check": is_check,
        "index": is_index,
        "orders": orders,
        "type": _type,
    }


class DatabaseIntrospection(BaseDatabaseIntrospection):
    """Encapsulate backends-specific introspection utilities."""

    # Reverse mapping from a YDB column type name (as produced by
    # _ydb_type_name and stored in FieldInfo.type_code) to a Django field type.
    # Used by Django introspection and `inspectdb`. The mapping is necessarily
    # lossy because several Django fields share one YDB type (e.g. CharField and
    # TextField both map to Utf8).
    data_types_reverse = {
        "Bool": "BooleanField",
        "Int8": "SmallIntegerField",
        "Int16": "SmallIntegerField",
        "Int32": "IntegerField",
        "Int64": "BigIntegerField",
        "Uint8": "PositiveSmallIntegerField",
        "Uint16": "PositiveSmallIntegerField",
        "Uint32": "PositiveIntegerField",
        "Uint64": "PositiveBigIntegerField",
        "Float": "FloatField",
        "Double": "FloatField",
        "Decimal": "DecimalField",
        "Utf8": "TextField",
        "String": "BinaryField",
        "Json": "JSONField",
        "JsonDocument": "JSONField",
        "Yson": "TextField",
        "UUID": "UUIDField",
        "Date": "DateField",
        "Datetime": "DateTimeField",
        "Timestamp": "DateTimeField",
        "Interval": "DurationField",
    }

    def get_yql_type(self, internal_type):
        """
        Forward map a Django field internal type to the YQL type string used in
        ``DECLARE`` statements. Auto-increment fields are declared as their
        underlying integer type because ``Serial`` cannot be used as a
        parameter type.
        """
        if internal_type == "SmallAutoField":
            return "Int16"
        if internal_type == "AutoField":
            return "Int32"
        if internal_type == "BigAutoField":
            return "Int64"
        return self.connection.data_types[internal_type]

    def get_field_type(self, data_type, description):
        """
        Hook for a database backend to use the cursor description to match a
        Django field type to a database column. ``data_type`` is the YDB type
        name stored in ``FieldInfo.type_code``.
        """
        return self.data_types_reverse.get(data_type, "TextField")

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
        is a dict: {'table': <table_name>, 'column': <column_name>}.

        YDB does not expose Serial metadata through describe(), so only
        integer primary key columns (the shape produced by Django's auto
        fields) are reported as sequences.
        """
        table_scheme_entry = self.connection.get_describe(table_name)
        primary_key = set(table_scheme_entry.primary_key)
        sequences = []
        for column in table_scheme_entry.columns:
            if column.name not in primary_key:
                continue
            base_type, _ = _resolve_base_type(column.type)
            if _ydb_type_name(base_type) in _INTEGER_TYPE_NAMES:
                sequences.append({"table": table_name, "column": column.name})
        return sequences

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
        return list(table_scheme_entry.primary_key)

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

        YDB exposes neither foreign keys nor check constraints, and its
        secondary indexes are not unique, so those are reported accordingly.
        """
        constraints = {}
        table_scheme_entry = self.connection.get_describe(table_name)

        if table_scheme_entry.primary_key:
            pk_columns = list(table_scheme_entry.primary_key)
            constraints["primary_key"] = _get_constraint_tuple(
                columns=pk_columns,
                is_primary_key=True,
                is_unique=True,
                orders=["ASC"] * len(pk_columns),
            )

        for index in table_scheme_entry.indexes:
            columns = list(index.index_columns)
            constraints[index.name] = _get_constraint_tuple(
                columns=columns,
                is_primary_key=False,
                # YDB secondary indexes do not enforce uniqueness.
                is_unique=False,
                orders=["ASC"] * len(columns),
                _type="global",
            )

        return constraints
