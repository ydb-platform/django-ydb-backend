from django.db.backends.base.introspection import BaseDatabaseIntrospection, TableInfo


class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        'Uint64': 'BigAutoField',
        'Bool': 'BooleanField',
        'Utf8': 'TextField',
        'String': 'BinaryField',
        'Date': 'DateField',
        'Datetime': 'DateTimeField',
        'Timestamp': 'DateTimeField',
        'Interval': 'DurationField',
        'Double': 'FloatField',
        'Float': 'FloatField',
        'Int32': 'IntegerField',
        'Int64': 'BigIntegerField',
        'Uint32': 'PositiveIntegerField',
        'Uint16': 'PositiveSmallIntegerField',
        'Int16': 'SmallIntegerField',
        'Json': 'JSONField',
        'Decimal': 'DecimalField',
    }

    def get_field_type(self, data_type, description):
        field_type = super().get_field_type(data_type, description)

        if description.is_autofield:
            if field_type == 'IntegerField':
                return 'AutoField'
            elif field_type == 'BigIntegerField':
                return 'BigAutoField'
            elif field_type == 'SmallIntegerField':
                return 'SmallAutoField'

        # Обработка UUID
        if data_type == 'UUID':
            return 'UUIDField'

        # Обработка IP-адресов
        if data_type == 'IPAddress':
            return 'GenericIPAddressField'

        # Обработка JSON
        if data_type == 'Json':
            return 'JSONField'

        return field_type

    # не уверен что from существует, ничего другого не нашел
    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute("SELECT table_name, type FROM system.tables")
        return [TableInfo(*row) for row in cursor.fetchall()]

    # не уверен что правильно, ничего другого не нашел
    def get_table_description(self, cursor, table_name):
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()

    def get_sequences(self, cursor, table_name, table_fields=()):
        # YDB does not support sequences
        return []

    def get_relations(self, cursor, table_name):
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        relations = {}
        for row in cursor.fetchall():
            relations[row[3]] = (row[2], row[0])  # {field_name: (other_table, other_field)}
        return relations

    def get_constraints(self, cursor, table_name):
        constraints = {}
        # Получаем информацию о первичных ключах
        cursor.execute(f"PRAGMA table_info({table_name})")
        for row in cursor.fetchall():
            if row[5]:  # Если столбец является первичным ключом
                constraints[f"primary_key_{row[1]}"] = {
                    'columns': [row[1]],
                    'primary_key': True,
                    'unique': False,
                    'foreign_key': None,
                    'check': False,
                    'index': False,
                }
        # Получаем информацию об индексах
        cursor.execute(f"PRAGMA index_list({table_name})")
        for row in cursor.fetchall():
            constraints[row[1]] = {
                'columns': [row[2]],
                'primary_key': False,
                'unique': row[3],
                'foreign_key': None,
                'check': False,
                'index': True,
            }
        return constraints
