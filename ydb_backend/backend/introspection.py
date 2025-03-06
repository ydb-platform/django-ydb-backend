from django.db.backends.base.introspection import BaseDatabaseIntrospection


class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        "Uint64": "BigAutoField",
        "Bool": "BooleanField",
        "Utf8": "TextField",
        "String": "BinaryField",
        "Date": "DateField",
        "Datetime": "DateTimeField",
        "Timestamp": "DateTimeField",
        "Interval": "DurationField",
        "Double": "FloatField",
        "Float": "FloatField",
        "Int32": "IntegerField",
        "Int64": "BigIntegerField",
        "Uint32": "PositiveIntegerField",
        "Uint16": "PositiveSmallIntegerField",
        "Int16": "SmallIntegerField",
        "Json": "JSONField",
        "Decimal": "DecimalField",
    }

    def get_field_type(self, data_type, description):
        """
        Hook for a database backend to use the cursor description to
        match a Django field type to a database column.

        For Oracle, the column data_type on its own is insufficient to
        distinguish between a FloatField and IntegerField, for example.
        """

        field_type = super().get_field_type(data_type, description)

        if description.is_autofield:
            if field_type == "IntegerField":
                return "AutoField"
            if field_type == "BigIntegerField":
                return "BigAutoField"
            if field_type == "SmallIntegerField":
                return "SmallAutoField"

        if data_type == "UUID":
            return "UUIDField"

        if data_type == "IPAddress":
            return "GenericIPAddressField"

        if data_type == "Json":
            return "JSONField"

        return field_type

    def get_table_list(self, cursor):
        """
        Return an unsorted list of TableInfo named tuples of all tables and
        views that exist in the database.
        """
        return self.connection.get_table_names()

    def table_names(self, cursor=None, include_views=False):
        """
        Return a list of names of all tables that exist in the database.
        Sort the returned table list by Python's default sorting. Do NOT use
        the database's ORDER BY here to avoid subtle differences in sorting
        order between databases.
        """

        return sorted(ti.name for ti in self.get_table_list(cursor) if include_views)

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()

    def get_sequences(self, cursor, table_name, table_fields=()):
        # YDB does not support sequences
        return []

    def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all foreign keys in the given table.
        """
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        relations = {}
        for row in cursor.fetchall():
            relations[row[3]] = (
                row[2],
                row[0],
            )  # {field_name: (other_table, other_field)}
        return relations

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
        cursor.execute(f"PRAGMA table_info({table_name})")
        for row in cursor.fetchall():
            if row[5]:  # Если столбец является первичным ключом
                constraints[f"primary_key_{row[1]}"] = {
                    "columns": [row[1]],
                    "primary_key": True,
                    "unique": False,
                    "foreign_key": None,
                    "check": False,
                    "index": False,
                }
        # Получаем информацию об индексах
        cursor.execute(f"PRAGMA index_list({table_name})")
        for row in cursor.fetchall():
            constraints[row[1]] = {
                "columns": [row[2]],
                "primary_key": False,
                "unique": row[3],
                "foreign_key": None,
                "check": False,
                "index": True,
            }
        return constraints
