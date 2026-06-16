import datetime
import json

from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.models.functions import Now
from django.db.models.functions import Substr


def _now_as_ydb(self, compiler, connection, **extra_context):
    # YQL has no CURRENT_TIMESTAMP literal (Now's default template); use the
    # CurrentUtcTimestamp() built-in. Dispatched via Func.as_<vendor>, so this
    # only affects the YDB backend.
    return self.as_sql(
        compiler, connection, template="CurrentUtcTimestamp()", **extra_context
    )


Now.as_ydb = _now_as_ydb


def _substr_as_ydb(self, compiler, connection, **extra_context):  # noqa: ARG001
    # YQL's SUBSTRING built-in rejects Utf8 (CharField/TextField map to Utf8)
    # and is 0-indexed, whereas Django's Substr is 1-indexed. Use the
    # Utf8-native Unicode::Substring and shift the position by one.
    source, pos, *length = self.source_expressions
    source_sql, params = compiler.compile(source)
    pos_sql, pos_params = compiler.compile(pos)
    # Unicode::Substring takes Uint64 offsets; Django's pos is 1-based and
    # bound as a signed integer, so shift to 0-based and cast.
    parts = [source_sql, f"CAST(({pos_sql}) - 1 AS Uint64)"]
    params = [*params, *pos_params]
    if length:
        length_sql, length_params = compiler.compile(length[0])
        parts.append(f"CAST({length_sql} AS Uint64)")
        params.extend(length_params)
    return f"Unicode::Substring({', '.join(parts)})", params


Substr.as_ydb = _substr_as_ydb

DATE_PARAMS_EXTRACT = [
    "year",
    "day",
    "day_of_year",
    "month",
    "month_name",
    "week_of_year",
    "iso_week_of_year",
    "day_of_month",
    "day_of_week",
    "day_of_week_name",
    # Django's standard Extract lookup names.
    "week_day",
    "iso_week_day",
    "week",
    "quarter",
]

DATE_PARAMS_TRUNC = [
    "year",
    "quarter",
    "month",
    "week",
    "day",
]


# common code for methods date_extract_sql and datetime_extract_sql
def _common_dt_dttm_extract_funcs(lookup_type, sql, params):
    if lookup_type == "year":
        return f"DateTime::GetYear({sql})", params
    if lookup_type == "day_of_year":
        return f"DateTime::GetDayOfYear({sql})", params
    if lookup_type == "month":
        return f"DateTime::GetMonth({sql})", params
    if lookup_type == "month_name":
        return f"DateTime::GetMonthName({sql})", params
    if lookup_type == "week_of_year":
        return f"DateTime::GetWeekOfYear({sql})", params
    if lookup_type == "iso_week_of_year":
        return f"DateTime::GetWeekOfYearIso8601({sql})", params
    if lookup_type in ("day", "day_of_month"):
        return f"DateTime::GetDayOfMonth({sql})", params
    if lookup_type == "day_of_week":
        return f"DateTime::GetDayOfWeek({sql})", params
    if lookup_type == "day_of_week_name":
        return f"DateTime::GetDayOfWeekName({sql})", params
    # Django's ``__week_day`` numbers days 1=Sunday..7=Saturday, while YDB's
    # GetDayOfWeek is 1=Monday..7=Sunday; convert between the two conventions.
    if lookup_type == "week_day":
        return f"((DateTime::GetDayOfWeek({sql}) % 7) + 1)", params
    # Django's ``__iso_week_day`` is 1=Monday..7=Sunday, matching GetDayOfWeek.
    if lookup_type == "iso_week_day":
        return f"DateTime::GetDayOfWeek({sql})", params
    if lookup_type == "week":
        return f"DateTime::GetWeekOfYearIso8601({sql})", params
    if lookup_type == "quarter":
        return f"((DateTime::GetMonth({sql}) - 1) / 3 + 1)", params
    msg = f"Unsupported lookup type: {lookup_type}"
    raise ValueError(msg)


# common code for methods date_trunc_sql and datetime_trunc_sql
def _common_dt_dttm_trunc_funcs(lookup_type, sql, params):
    if lookup_type == "year":
        return f"DateTime::StartOfYear({sql})", params
    if lookup_type == "quarter":
        return f"DateTime::StartOfQuarter({sql})", params
    if lookup_type == "month":
        return f"Datetime::StartOfMonth({sql})", params
    if lookup_type == "week":
        return f"Datetime::StartOfWeek({sql})", params
    if lookup_type == "day":
        return f"Datetime::StartOfDay({sql})", params
    msg = f"Unsupported lookup type: {lookup_type}"
    raise ValueError(msg)


def _add_tzname(sql, tzname):
    if tzname:
        sql = f"AddTimezone({sql}, '{tzname}')"
    return sql


class DatabaseOperations(BaseDatabaseOperations):
    """
    Encapsulate backends-specific differences, such as the way a backends
    performs ordering or calculates the ID of a recently-inserted row.
    """

    compiler_module = "ydb_backend.models.sql.compiler"

    # Mapping of Field.get_internal_type() (typically the model field's class
    # name) to the data type to use for the Cast() function, if different from
    # DatabaseWrapper.data_types.
    cast_data_types = {
        "SmallAutoField": "CAST(%(expression)s AS Int16)",
        "AutoField": "CAST(%(expression)s AS Int32)",
        "BigAutoField": "CAST(%(expression)s AS Int64)",
        "BinaryField": "CAST(%(expression)s AS String)",
        "BooleanField": "CAST(%(expression)s AS Bool)",
        "CharField": "CAST(%(expression)s AS Utf8)",
        "DateField": "CAST(%(expression)s AS Date32)",
        "DateTimeField": "CAST(%(expression)s AS Timestamp64)",
        "DecimalField": "CAST(%(expression)s AS "
        "Decimal(%(max_digits)s, %(decimal_places)s))",
        "DurationField": "CAST(%(expression)s AS Interval)",
        "FileField": "CAST(%(expression)s AS String)",
        "FilePathField": "CAST(%(expression)s AS Utf8)",
        "FloatField": "CAST(%(expression)s AS Float)",
        "DoubleField": "CAST(%(expression)s AS Double)",
        "IntegerField": "CAST(%(expression)s AS Int32)",
        "BigIntegerField": "CAST(%(expression)s AS Int64)",
        "IPAddressField": "CAST(%(expression)s AS Utf8)",
        "GenericIPAddressField": "CAST(%(expression)s AS Utf8)",
        "NullBooleanField": "CAST(%(expression)s AS Bool)",
        "JSONField": "CAST(%(expression)s AS Json)",
        "PositiveIntegerField": "CAST(%(expression)s AS Uint32)",
        "PositiveSmallIntegerField": "CAST(%(expression)s AS Uint16)",
        "PositiveBigIntegerField": "CAST(%(expression)s AS Uint64)",
        "SmallIntegerField": "CAST(%(expression)s AS Int16)",
        "TextField": "CAST(%(expression)s AS Utf8)",
        "UUIDField": "CAST(%(expression)s AS UUID)",
    }

    # Integer field safe ranges by `internal_type` as documented
    # in docs/ref/models/fields.txt.
    integer_field_ranges = {
        **BaseDatabaseOperations.integer_field_ranges,
    }

    set_operators = {
        "union": "UNION",
    }

    # CharField data type if the max_length argument isn't provided.
    cast_char_field_without_max_length = "String"

    # TODO: try to understand why this method is needed.
    def format_for_duration_arithmetic(self, sql):
        return f"DateTime::ToMicroseconds({sql})"

    def date_extract_sql(self, lookup_type, sql, params):
        """
        Given a lookup_type of 'year', 'month', or 'day', return the SQL that
        extracts a value from the given date field field_name.
        """
        return _common_dt_dttm_extract_funcs(lookup_type, sql, params)

    def date_trunc_sql(self, lookup_type, sql, params, tzname=None):
        """
        iven a lookup_type of 'year', 'month', or 'day', return the SQL that
        truncates the given date or datetime field field_name to a date object
        with only the given specificity.

        If `tzname` is provided, the given value is truncated in a specific
        timezone.
        """
        sql = _add_tzname(sql, tzname)
        return _common_dt_dttm_trunc_funcs(lookup_type, sql, params)

    def datetime_cast_date_sql(self, sql, params, tzname):
        """
        Return the SQL to cast a datetime value to date value.
        """
        sql = _add_tzname(sql, tzname)
        # Date32 (signed/wide) so casting from a Timestamp64 / TzTimestamp64
        # works; the narrow Date type rejects it.
        return f"cast({sql} as Date32)", params

    def datetime_cast_time_sql(self, sql, params, tzname):
        """
        Return the SQL to cast a datetime value to time value.
        """
        sql = _add_tzname(sql, tzname)
        return f"DateTime::Format('%H:%M:%S %Z')({sql})", params

    def datetime_extract_sql(self, lookup_type, sql, params, tzname):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute', or
        'second', return the SQL that extracts a value from the given
        datetime field field_name.
        """
        sql = _add_tzname(sql, tzname)

        if lookup_type in DATE_PARAMS_EXTRACT:
            return _common_dt_dttm_extract_funcs(lookup_type, sql, params)
        if lookup_type == "hour":
            return f"DateTime::GetHour({sql})", params
        if lookup_type == "minute":
            return f"DateTime::GetMinute({sql})", params
        if lookup_type == "second":
            return f"DateTime::GetSecond({sql})", params
        if lookup_type == "millisecond":
            return f"DateTime::GetMillisecondOfSecond({sql})", params
        if lookup_type == "microsecond":
            return f"DateTime::GetMicrosecondOfSecond({sql})", params
        if lookup_type == "timezone_id":
            return f"DateTime::GetTimezoneId({sql})", params
        if lookup_type == "timezone_name":
            return f"DateTime::GetTimezoneName({sql})", params
        msg = f"Unsupported lookup type: {lookup_type}"
        raise ValueError(msg)

    def datetime_trunc_sql(self, lookup_type, sql, params, tzname):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute', or
        'second', return the SQL that truncates the given datetime field
        field_name to a datetime object with only the given specificity.
        """
        sql = _add_tzname(sql, tzname)

        if lookup_type in DATE_PARAMS_TRUNC:
            return _common_dt_dttm_trunc_funcs(lookup_type, sql, params)
        if lookup_type == "hour":
            return f"DateTime::StartOf(({sql}), Interval('PT1H'))", params
        if lookup_type == "minute":
            return f"DateTime::StartOf(({sql}), Interval('PT1M'))", params
        if lookup_type == "second":
            return f"DateTime::StartOf(({sql}), Interval('PT1S'))", params
        if lookup_type == "millisecond":
            return f"DateTime::StartOf(({sql}), Interval('PT01S'))", params

        msg = f"Unsupported lookup type: {lookup_type}"
        raise ValueError(msg)

    def time_trunc_sql(self, lookup_type, sql, params, tzname=None):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute', or
        'second', return the SQL that truncates the given datetime field
        field_name to a datetime object with only the given specificity.
        """
        return self.datetime_trunc_sql(lookup_type, sql, params, tzname)

    def no_limit_value(self):
        """
        Return the value to use for the LIMIT when we are wanting "LIMIT
        infinity". Return None if the limit clause can be omitted in this case.
        """

    def quote_name(self, name):
        """
        Return a quoted version of the given table, index, or column name. Do
        not quote the given name if it's already been quoted.
        """
        if name.startswith("`") and name.endswith("`"):
            return name
        return f"`{name}`"

    def regex_lookup(self, lookup_type):
        """
        Return the string to use in a query when performing regular expression
        lookups (using "regex" or "iregex"). It should contain a '%s'
        placeholder for the column being searched against.

        If the feature is not supported (or part of it is not supported), raise
        NotImplementedError.
        """
        if lookup_type == "regex":
            return "%s REGEXP %s"
        if lookup_type == "iregex":
            return "Unicode::ToLower(%s) REGEXP Unicode::ToLower(%s)"
        msg = f"Lookup '{lookup_type}' is not supported."
        raise NotImplementedError(msg)

    def prep_for_like_query(self, x):
        """Escape LIKE/ILIKE wildcards, using '~' as the ESCAPE character.

        YQL rejects the SQL-default '\\' (and '%'/'_') in the ESCAPE clause, so
        the backslash-based default cannot be used here. The escape character
        itself is escaped first; this matches ``ESCAPE '~'`` in
        ``DatabaseWrapper.operators`` and ``pattern_ops``.
        """
        return str(x).replace("~", "~~").replace("%", "~%").replace("_", "~_")

    # TODO: try to understand what is the param 'style'.
    def sql_flush_table(self, style, table):
        """
        Return a list of SQL statements required to remove all data from
        the given database tables (without actually removing the tables
        themselves).

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.

        If `reset_sequences` is True, the list includes SQL statements required
        to reset the sequences.

        The `allow_cascade` argument determines whether truncation may cascade
        to tables with foreign keys pointing the tables being truncated.
        PostgreSQL requires a cascade even if these tables are empty.
        """
        sql_keyword = style.SQL_KEYWORD("DELETE FROM")
        sql_field = style.SQL_FIELD(self.quote_name(table))
        return f"{sql_keyword} {sql_field};"

    def sql_flush(self, style, tables, *, reset_sequences=False, allow_cascade=False):
        if not tables:
            return []
        return [self.sql_flush_table(style, table) for table in tables]

    def time_extract_sql(self, lookup_type, sql, params):
        """
        Given a lookup_type of 'hour', 'minute', or 'second', return the SQL
        that extracts a value from the given time field field_name.
        """
        return self.datetime_extract_sql(lookup_type, sql, params, tzname=None)

    # TODO: Double check
    def last_executed_query(self, cursor, sql, params):
        """
        Return a string of the query last executed by the given cursor, with
        placeholders replaced with actual values.

        `sql` is the raw query containing placeholders and `params` is the
        sequence of parameters. These are used by default, but this method
        exists for database backends to provide a better implementation
        according to their own quoting schemes.
        """

        # Convert params to contain string values.
        def to_string(s):
            return str(s)

        if params:
            if isinstance(params, list | tuple):
                sql = sql % tuple(map(to_string, params))
            elif params and isinstance(params, dict):
                formatted_sql = sql
                for param, value in params.items():
                    val = value[0] if isinstance(value, tuple) else value
                    str_val = to_string(val)
                    formatted_sql = formatted_sql.replace(param, str_val)
                return formatted_sql

        return sql

    def last_insert_id(self, cursor, table_name, pk_name):
        """
        Given a cursor object that has just performed an INSERT statement into
        a table that has an auto-incrementing ID, return the newly created ID.

        `pk_name` is the name of the primary-key column.
        """
        query = "SELECT %(pk)s FROM %(table)s ORDER BY %(pk)s DESC LIMIT 1"

        sql = query % {
            "table": self.quote_name(table_name),
            "pk": pk_name,
        }

        cursor.execute(sql)
        return cursor.fetchone()[0]

    def max_in_list_size(self):
        """
        Return the maximum number of items that can be passed in a single 'IN'
        list condition, or None if the backends does not impose a limit.
        """
        # YQL has a limit on the size of a query in bytes (about 1Mb)

    def max_name_length(self):
        """
        Return the maximum length of table and column names, or None if there
        is no limit.
        """
        # The maximum supported length of table and column names in ydb is 255
        return 255

    def pk_default_value(self):
        """
        Return the value to use during an INSERT statement to specify that
        the field should use its default value.
        """
        return "NULL"

    def prepare_sql_script(self, sql):
        """
        Take an SQL script that may contain multiple lines and return a list
        of statements to feed to successive cursor.execute() calls.

        Since few databases are able to process raw SQL scripts in a single
        cursor.execute() call and PEP 249 doesn't talk about this use case,
        the default implementation is conservative.
        """
        return [stmt.strip() + ";" for stmt in sql.split(";") if stmt.strip()]

    def adapt_datefield_value(self, value):
        """
        Transform a date value to an object compatible with what is expected
        by the backends driver for date columns.
        """
        return value

    def adapt_datetimefield_value(self, value):
        """
        Transform a datetime value to an object compatible with what is expected
        by the backends driver for datetime columns.
        """
        return value

    def adapt_timefield_value(self, value):
        """
        Transform a time value to an object compatible with what is expected
        by the backends driver for time columns.
        """
        return value

    def get_db_converters(self, expression):
        converters = super().get_db_converters(expression)
        if expression.output_field.get_internal_type() == "TimeField":
            converters.append(self.convert_timefield_value)
        return converters

    def convert_timefield_value(self, value, expression, connection):
        """
        Rebuild a ``time`` from the Int64 microseconds-since-midnight a
        ``TimeField`` is stored as (see DatabaseWrapper.data_types).
        """
        if value is None or isinstance(value, datetime.time):
            return value
        seconds, microsecond = divmod(int(value), 1_000_000)
        minutes, second = divmod(seconds, 60)
        hour, minute = divmod(minutes, 60)
        return datetime.time(hour, minute, second, microsecond)

    def adapt_decimalfield_value(self, value, max_digits=None, decimal_places=None):
        """
        Transform a decimal.Decimal value to an object compatible with what is
        expected by the backends driver for decimal (numeric) columns.
        """
        return value

    def adapt_ipaddressfield_value(self, value):
        """
        Transform a string representation of an IP address into the expected
        type for the backends driver.
        """
        return value

    def adapt_json_value(self, value, encoder):
        return json.dumps(value, cls=encoder)

    def bulk_insert_sql(self, fields, placeholder_rows):
        placeholder_rows_sql = (", ".join(row) for row in placeholder_rows)
        values_sql = ", ".join([f"({sql})" for sql in placeholder_rows_sql])
        return f"VALUES {values_sql}"

    def savepoint_commit_sql(self, sid):
        """
        Savepoint operations are not supported in YDB - empty stub for Django
        """

    def savepoint_rollback_sql(self, sid):
        """
        Savepoint operations are not supported in YDB - empty stub for Django
        """

    def upsert_statement(self, on_conflict=None):
        # YDB's UPSERT INTO inserts missing rows and overwrites the listed
        # columns of existing rows, keyed on the primary key. on_conflict is
        # accepted for parity with insert_statement(); YDB has no conflict
        # clause to emit.
        return "UPSERT INTO"
