import re

import ydb
from django.core.exceptions import EmptyResultSet
from django.core.exceptions import FieldError
from django.core.exceptions import FullResultSet
from django.db import NotSupportedError
from django.db.models.expressions import RawSQL
from django.db.models.sql import compiler
from django.db.models.sql.compiler import SQLAggregateCompiler
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query

_ydb_types = {
    "AutoField": ydb.PrimitiveType.Int32,
    "BigAutoField": ydb.PrimitiveType.Int64,
    "BinaryField": ydb.PrimitiveType.Utf8,
    "BooleanField": ydb.PrimitiveType.Bool,
    # TODO: make the method limit the number of characters
    "CharField": ydb.PrimitiveType.Utf8,
    "DateField": ydb.PrimitiveType.Date,
    "DateTimeField": ydb.PrimitiveType.Datetime,
    "DurationField": ydb.PrimitiveType.Interval,
    "FileField": ydb.PrimitiveType.Utf8,
    "FilePathField": ydb.PrimitiveType.Utf8,
    "FloatField": ydb.PrimitiveType.Float,
    "DoubleField": ydb.PrimitiveType.Double,
    "IntegerField": ydb.PrimitiveType.Int32,
    "BigIntegerField": ydb.PrimitiveType.Int64,
    "IPAddressField": ydb.PrimitiveType.Utf8,
    "GenericIPAddressField": ydb.PrimitiveType.Utf8,
    "OneToOneField": ydb.PrimitiveType.Int64,
    "PositiveIntegerField": ydb.PrimitiveType.Uint32,
    "PositiveBigIntegerField": ydb.PrimitiveType.Uint64,
    "PositiveSmallIntegerField": ydb.PrimitiveType.Uint16,
    "SlugField": ydb.PrimitiveType.Utf8,
    "SmallAutoField": ydb.PrimitiveType.Int16,
    "SmallIntegerField": ydb.PrimitiveType.Int16,
    "TextField": ydb.PrimitiveType.Utf8,
    "TimeField": ydb.PrimitiveType.Timestamp,
    "UUIDField": ydb.PrimitiveType.UUID,
    "JSONField": ydb.PrimitiveType.Json,
}


def _extract_column_names(sql):
    sql = re.sub(r"'[^']*'", "", sql)
    sql = re.sub(r'"[^"]*"', "", sql)
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

    pattern = r"""
        (?:`\w+`\.)?
        `(?P<column>\w+)`
        \s*
        (?:
          <>|<=|>=|=|!=|
          <|>|LIKE|IN|
          IS(?:\s+NOT)?
        )
        \s*%s
    """

    columns = []
    for match in re.finditer(pattern, sql, re.VERBOSE | re.IGNORECASE):
        columns.append(match.group("column"))

    return columns


def _replace_placeholders(sql):
    placeholder_rows = []
    counter = 1

    while "%s" in sql:
        sql = sql.replace("%s", f"${'element_' + str(counter)}", 1)
        placeholder_rows.append("$element_" + str(counter))
        counter += 1

    return sql, placeholder_rows


def _generate_params_for_update(placeholder_rows, columns, field_types, params):
    model_types = []

    for column in columns:
        if column in field_types:
            model_types.append(field_types[column])

    modified_params = {}

    for i in range(len(placeholder_rows)):
        if str(model_types[i]) == "DateTimeField":
            modified_params[placeholder_rows[i]] = (
                int(params[i].timestamp()),
                _ydb_types[model_types[i]]
            )
        else:
            modified_params[placeholder_rows[i]] = (
                params[i],
                _ydb_types[model_types[i]]
            )

    return modified_params


def _get_data(fields, param_rows):
    result = []

    for i in range(len(param_rows)):
        struct = {}
        for j in range(len(fields)):
            if fields[j].get_internal_type() == "DateTimeField":
                struct[fields[j].column] = int(param_rows[i][j].timestamp())
            else:
                struct[fields[j].column] = param_rows[i][j]
        result.append(struct)

    return result


def _get_data_type(fields):
    struct_type = ydb.StructType()
    for f in fields:
        struct_type.add_member(f.column, _ydb_types[f.get_internal_type()])
    return ydb.ListType(struct_type)


class SQLCompiler(SQLCompiler):
    def as_sql(self, with_limits=True, with_col_aliases=False):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.

        If 'with_limits' is False, any limit/offset information is not included
        in the query.
        """

        refcounts_before = self.query.alias_refcount.copy()
        columns = []
        try:
            combinator = self.query.combinator
            extra_select, order_by, group_by = self.pre_sql_setup(
                with_col_aliases=with_col_aliases or bool(combinator),
            )
            # Is a LIMIT/OFFSET clause needed?
            with_limit_offset = with_limits and self.query.is_sliced
            combinator = self.query.combinator
            features = self.connection.features
            if combinator:
                if not getattr(features, f"supports_select_{combinator}"):
                    msg = f"{combinator} is not supported on this database backend."
                    raise NotSupportedError(msg)
                result, params = self.get_combinator_sql(
                    combinator, self.query.combinator_all
                )
            elif self.qualify:
                result, params = self.get_qualify_sql()
                order_by = None
            else:
                distinct_fields, distinct_params = self.get_distinct()
                # This must come after 'select', 'ordering', and 'distinct'
                # (see docstring of get_from_clause() for details).
                from_, f_params = self.get_from_clause()
                try:
                    where, w_params = (
                        self.compile(self.where) if self.where is not None else ("", [])
                    )
                except EmptyResultSet:
                    if self.elide_empty:
                        raise
                    # Use a predicate that's always False.
                    where, w_params = "0 = 1", []
                except FullResultSet:
                    where, w_params = "", []
                try:
                    having, h_params = (
                        self.compile(self.having)
                        if self.having is not None
                        else ("", [])
                    )
                except FullResultSet:
                    having, h_params = "", []
                result = ["SELECT"]
                params = []

                if self.query.distinct:
                    distinct_result, distinct_params = self.connection.ops.distinct_sql(
                        distinct_fields,
                        distinct_params,
                    )
                    result += distinct_result
                    params += distinct_params

                out_cols = []
                for _, (s_sql, s_params), alias in self.select + extra_select:
                    columns = columns + _extract_column_names(s_sql)
                    if alias:
                        s_sql = f"{s_sql} AS {self.connection.ops.quote_name(alias)}"  # noqa: PLW2901
                    params.extend(s_params)
                    out_cols.append(s_sql)

                result += [", ".join(out_cols)]

                if from_:
                    result += ["FROM", *from_]
                elif self.connection.features.bare_select_suffix:
                    result += [self.connection.features.bare_select_suffix]
                params.extend(f_params)

                if where:
                    result.append(f"WHERE {where}")
                    params.extend(w_params)
                    if len(where) > 0:
                        col = re.findall(r"`\w+`\.`(\w+)`", where)
                        columns = columns + col

                grouping = []
                for g_sql, g_params in group_by:
                    grouping.append(g_sql)
                    params.extend(g_params)
                if grouping:
                    if distinct_fields:
                        raise NotImplementedError(
                            "annotate() + distinct(fields) is not implemented."
                        )
                    order_by = order_by or self.connection.ops.force_no_ordering()
                    result.append(f"GROUP BY {', '.join(grouping)}")
                    if self._meta_ordering:
                        order_by = None
                if having:
                    if not grouping:
                        result.extend(self.connection.ops.force_group_by())
                    result.append(f"HAVING {having}")
                    params.extend(h_params)
                    if len(having) > 0:
                        col = re.findall(r"`\w+`\.`(\w+)`", having)
                        columns = columns + col

            if self.query.explain_info:
                result.insert(
                    0,
                    self.connection.ops.explain_query_prefix(
                        self.query.explain_info.format,
                        **self.query.explain_info.options,
                    ),
                )

            if order_by:
                ordering = []
                for _, (o_sql, o_params, _) in order_by:
                    ordering.append(o_sql)
                    params.extend(o_params)
                order_by_sql = f"ORDER BY {', '.join(ordering)}"
                if combinator and features.requires_compound_order_by_subquery:
                    result = ["SELECT * FROM (", *result, ")", order_by_sql]
                else:
                    result.append(order_by_sql)

            if with_limit_offset:
                result.append(
                    self.connection.ops.limit_offset_sql(
                        self.query.low_mark, self.query.high_mark
                    )
                )

            if self.query.subquery and extra_select:
                # If the query is used as a subquery, the extra selects would
                # result in more columns than the left-hand side expression is
                # expecting. This can happen when a subquery uses a combination
                # of order_by() and distinct(), forcing the ordering expressions
                # to be selected as well. Wrap the query in another subquery
                # to exclude extraneous selects.
                sub_selects = []
                sub_params = []
                for _index, (select, _, alias) in enumerate(self.select, start=1):
                    if alias:
                        sub_selects.append(
                            f"{self.connection.ops.quote_name('subquery')}."
                            f"{self.connection.ops.quote_name(alias)}"
                        )
                    else:
                        select_clone = select.relabeled_clone(
                            {select.alias: "subquery"}
                        )
                        subselect, subparams = select_clone.as_sql(
                            self, self.connection
                        )
                        sub_selects.append(subselect)
                        sub_params.extend(subparams)
                sql, params = (
                    f"SELECT {', '.join(sub_selects)} "
                    f"FROM ({' '.join(result)}) subquery",
                    tuple(sub_params + params),
                )

                return sql, params

            sql, params = " ".join(result), tuple(params)
            sql, placeholder_rows = _replace_placeholders(sql)

            field_types = {
                field.name: field.get_internal_type()
                for field in self.query.model._meta.get_fields()
                if hasattr(field, "name")
            }

            modified_params = _generate_params_for_update(
                placeholder_rows, columns, field_types, params
            )

            return sql, modified_params
        finally:
            # Finally do cleanup - get rid of the joins we created above.
            self.query.reset_refcounts(refcounts_before)


class BaseSQLWriteCompiler(compiler.SQLInsertCompiler):
    def _prepare_sql_statement(self):
        qn = self.connection.ops.quote_name
        opts = self.query.get_meta()
        fields = self.query.fields or [opts.pk]

        field_types = [
            qn(f.column) + ": " + self.connection.introspection.get_field_type(
                f.get_internal_type(), {}
            )
            for f in fields
        ]
        in_ = f"{', '.join(field_types)}"

        return [
            f"DECLARE $in_ as List<Struct<{in_}>>;",
            f"{self._get_statement()} {qn(opts.db_table)}",
            f"({', '.join(qn(f.column) for f in fields)})",
            f"SELECT {', '.join(qn(f.column) for f in fields)} FROM AS_TABLE($in_);"
        ]

    def _prepare_params(self):
        opts = self.query.get_meta()
        fields = self.query.fields or [opts.pk]

        if self.query.fields:
            value_rows = [
                [
                    self.prepare_value(field, self.pre_save_val(field, obj))
                    for field in fields
                ]
                for obj in self.query.objs
            ]
        else:
            value_rows = [
                [self.connection.ops.pk_default_value()] for _ in self.query.objs
            ]
            fields = [None]

        _, param_rows = self.assemble_as_sql(fields, value_rows)
        return {
            "$in_": (
                _get_data(fields, param_rows),
                _get_data_type(fields)
            )
        }

    def _get_statement(self):
        raise NotImplementedError("Subclasses must implement this method")

    def as_sql(self):
        sql = self._prepare_sql_statement()
        params = self._prepare_params()
        return [(" ".join(sql), params)]

    def execute_sql(self, returning_fields=None):
        if returning_fields and len(self.query.objs) != 1:
            raise ValueError(
                "Invalid state: returning_fields requires "
                "exactly one object in query.objs"
            )

        opts = self.query.get_meta()
        self.returning_fields = returning_fields

        with self.connection.cursor() as cursor:
            for sql, params in self.as_sql():
                cursor.execute_scheme(sql, params)
            if not self.returning_fields:
                return []
            if (
                    self.connection.features.can_return_rows_from_bulk_insert
                    and len(self.query.objs) > 1
            ):
                rows = self.connection.ops.fetch_returned_insert_rows(cursor)
                cols = [field.get_col(opts.db_table) for field in self.returning_fields]
            else:
                cols = [opts.pk.get_col(opts.db_table)]
                rows = [
                    (
                        self.connection.ops.last_insert_id(
                            cursor,
                            opts.db_table,
                            opts.pk.column,
                        ),
                    )
                ]
        converters = self.get_converters(cols)
        if converters:
            rows = list(self.apply_converters(rows, converters))
        return rows


class SQLInsertCompiler(BaseSQLWriteCompiler):
    def _get_statement(self):
        return self.connection.ops.insert_statement(
            on_conflict=self.query.on_conflict,
        )


class SQLUpsertCompiler(BaseSQLWriteCompiler):
    def _get_statement(self):
        return self.connection.ops.upsert_statement(
            on_conflict=self.query.on_conflict,
        )


class SQLDeleteCompiler(compiler.SQLDeleteCompiler):
    def _as_sql(self, query):
        columns = []
        delete = f"DELETE FROM {self.quote_name_unless_alias(query.base_table)}"

        try:
            where, params = self.compile(query.where)
            if len(where) > 0:
                parts = where.split("%s")[:-1]
                for part in parts:
                    chunks = part.split("`")
                    column_name = chunks[-2].strip()
                    columns.append(column_name)
        except FullResultSet:
            return delete, ()
        sql, params = f"{delete} WHERE {where}", tuple(params)
        sql, placeholder_rows = _replace_placeholders(sql)

        field_types = {
            field.name: field.get_internal_type()
            for field in self.query.model._meta.get_fields()
            if hasattr(field, "name")
        }

        modified_params = _generate_params_for_update(
            placeholder_rows, columns, field_types, params
        )

        return sql, modified_params

    def as_sql(self):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.
        """
        if self.single_alias and (
                self.connection.features.delete_can_self_reference_subquery
                or not self.contains_self_reference_subquery
        ):
            return self._as_sql(self.query)
        innerq = self.query.clone()
        innerq.__class__ = Query
        innerq.clear_select_clause()
        pk = self.query.model._meta.pk
        innerq.select = [pk.get_col(self.query.get_initial_alias())]
        outerq = Query(self.query.model)
        if not self.connection.features.update_can_self_select:
            # Force the materialization of the inner query to allow reference
            # to the target table on MySQL.
            sql, params = innerq.get_compiler(connection=self.connection).as_sql()
            innerq = RawSQL(f"SELECT * FROM ({sql}) subquery", params) # noqa: S611
        outerq.add_filter("pk__in", innerq)
        return self._as_sql(outerq)


class SQLUpdateCompiler(compiler.SQLUpdateCompiler):
    def as_sql(self):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.
        """
        self.pre_sql_setup()
        if not self.query.values:
            return "", ()
        qn = self.quote_name_unless_alias
        values, update_params = [], []
        for field, _model, val in self.query.values:
            if hasattr(val, "resolve_expression"):
                val = val.resolve_expression(  # noqa: PLW2901
                    self.query, allow_joins=False, for_save=True
                )
                if val.contains_aggregate:
                    error_message = (
                        f"Aggregate functions are not allowed in this query "
                        f"({field.name}={val!r})."
                    )
                    raise FieldError(error_message)
                if val.contains_over_clause:
                    error_message = (
                        f"Window expressions are not allowed in this query "
                        f"({field.name}={val!r})."
                    )
                    raise FieldError(error_message)
            elif hasattr(val, "prepare_database_save"):
                if field.remote_field:
                    val = val.prepare_database_save(field)  # noqa: PLW2901
                else:
                    error_message = (
                        f"Tried to update field {field} "
                        f"with a model instance, {val!r}. "
                        f"Use a value compatible with {field.__class__.__name__}."
                    )
                    raise TypeError(error_message)
            val = field.get_db_prep_save(val, connection=self.connection)  # noqa: PLW2901

            # Getting the placeholder for the field.
            if hasattr(field, "get_placeholder"):
                placeholder = field.get_placeholder(val, self, self.connection)
            else:
                placeholder = "%s"
            name = field.column
            if hasattr(val, "as_sql"):
                sql, params = self.compile(val)
                values.append(f"{qn(name)} = {placeholder % sql}")
                update_params.extend(params)
            elif val is not None:
                values.append(f"{qn(name)} = {placeholder}")
                update_params.append(val)
            else:
                values.append(f"{qn(name)} = NULL")
        table = self.query.base_table

        result = [
            f"UPDATE {qn(table)} SET",
            ", ".join(values),
        ]

        columns = [item.split("=")[0].strip().strip("`") for item in values]

        try:
            where, params = self.compile(self.query.where)
            if len(where) > 0:
                parts = where.split("%s")[:-1]
                for part in parts:
                    chunks = part.split("`")
                    column_name = chunks[-2].strip()
                    columns.append(column_name)
        except FullResultSet:
            params = []
        else:
            result.append(f"WHERE {where}")

        sql, params = " ".join(result), tuple(update_params + params)
        sql, placeholder_rows = _replace_placeholders(sql)

        field_types = {
            field.name: field.get_internal_type()
            for field in self.query.model._meta.get_fields()
            if hasattr(field, "name")
        }

        modified_params = _generate_params_for_update(
            placeholder_rows, columns, field_types, params
        )
        return sql, modified_params

    # TODO: fix this method
    def execute_sql(self, returning_fields=None):
        """
        Execute the specified update. Return the number of rows affected by
        the primary update query. The "primary update query" is the first
        non-empty query that is executed. Row counts for any subsequent,
        related queries are not available.
        """
        self.returning_fields = returning_fields
        with self.connection.cursor() as cursor:
            sql, params = self.as_sql()
            cursor.execute(sql, params)
            if hasattr(cursor, "rowcount") and cursor.rowcount == -1:
                cursor.rowcount = 1
            return cursor.rowcount


class SQLAggregateCompiler(SQLAggregateCompiler):
    def as_sql(self):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.
        """
        sql, params = [], []
        for annotation in self.query.annotation_select.values():
            ann_sql, ann_params = self.compile(annotation)
            ann_sql, ann_params = annotation.select_format(self, ann_sql, ann_params)
            sql.append(ann_sql)
            params.extend(ann_params)
        self.col_count = len(self.query.annotation_select)
        sql = ", ".join(sql)
        params = tuple(params)

        inner_query_sql, inner_query_params = self.query.inner_query.get_compiler(
            self.using,
            elide_empty=self.elide_empty,
        ).as_sql(with_col_aliases=True)
        sql = f"SELECT {sql} FROM ({inner_query_sql}) subquery"
        params += inner_query_params
        return sql, params
