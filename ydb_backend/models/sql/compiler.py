from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import ydb
from django.core.exceptions import EmptyResultSet
from django.core.exceptions import FieldError
from django.core.exceptions import FullResultSet
from django.db import NotSupportedError
from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models.lookups import Lookup
from django.db.models.sql import compiler
from django.db.models.sql.compiler import SQLAggregateCompiler
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query

_ydb_types = {
    "AutoField": ydb.PrimitiveType.Int32,
    "BigAutoField": ydb.PrimitiveType.Int64,
    "BinaryField": ydb.PrimitiveType.String,
    "BooleanField": ydb.PrimitiveType.Bool,
    # TODO: make the method limit the number of characters
    "CharField": ydb.PrimitiveType.Utf8,
    "DateField": ydb.PrimitiveType.Date,
    "DateTimeField": ydb.PrimitiveType.Datetime,
    "DurationField": ydb.PrimitiveType.Interval,
    "FileField": ydb.PrimitiveType.String,
    "FilePathField": ydb.PrimitiveType.Utf8,
    "DecimalField": ydb.DecimalType(precision=22, scale=9),
    "FloatField": ydb.PrimitiveType.Float,
    "DoubleField": ydb.PrimitiveType.Double,
    "IntegerField": ydb.PrimitiveType.Int32,
    "BigIntegerField": ydb.PrimitiveType.Int64,
    "IPAddressField": ydb.PrimitiveType.Utf8,
    "GenericIPAddressField": ydb.PrimitiveType.Utf8,
    "PositiveIntegerField": ydb.PrimitiveType.Uint32,
    "PositiveBigIntegerField": ydb.PrimitiveType.Uint64,
    "PositiveSmallIntegerField": ydb.PrimitiveType.Uint16,
    "SlugField": ydb.PrimitiveType.Utf8,
    "SmallAutoField": ydb.PrimitiveType.Int16,
    "SmallIntegerField": ydb.PrimitiveType.Int16,
    "TextField": ydb.PrimitiveType.Utf8,
    "UUIDField": ydb.PrimitiveType.UUID,
    "JSONField": ydb.PrimitiveType.Json,
}


class _ParamTypingMixin:
    """
    Type query parameters from Django's expression tree instead of by
    regex-scanning the generated SQL.

    ``compile`` is overridden to record, for every emitted ``%s`` parameter, the
    Django internal field type it belongs to (or ``None`` when it cannot be
    determined). A lookup's value parameters are typed from the left-hand
    side's ``output_field``; nested expressions and subqueries are typed by
    their own compilation. Anything that cannot be resolved falls back to
    value-based inference downstream.
    """

    # Active capture buffer (a list parallel to the params produced) or None.
    _captured_types = None

    def compile(self, node):
        captured = self._captured_types
        base = len(captured) if captured is not None else 0
        sql, params = super().compile(node)
        if captured is not None and params:
            # Parameters not produced by a nested compile() are emitted directly
            # by this node (e.g. a lookup's right-hand value), so type them here.
            direct = len(params) - (len(captured) - base)
            if direct > 0:
                captured.extend([self._direct_internal_type(node)] * direct)
        return sql, params

    @staticmethod
    def _direct_internal_type(node):
        field = None
        try:
            field = node.lhs.output_field if isinstance(node, Lookup) else (
                node.output_field
            )
        except (FieldError, AttributeError):
            field = None
        if field is None:
            return None
        try:
            return _get_field_internal_type(field)
        except (FieldError, AttributeError):
            return None

    def _compile_capturing(self, node):
        """Compile ``node`` and also return the per-parameter internal types."""
        previous = self._captured_types
        self._captured_types = []
        try:
            sql, params = self.compile(node)
            return sql, params, list(self._captured_types)
        finally:
            self._captured_types = previous


def _replace_placeholders(sql):
    placeholder_rows = []
    counter = 1

    while "%s" in sql:
        sql = sql.replace("%s", f"${'element_' + str(counter)}", 1)
        placeholder_rows.append("$element_" + str(counter))
        counter += 1

    return sql, placeholder_rows


def _infer_ydb_type(value):
    """Infer a YDB type from a Python value when no column name is available."""
    if value is None:
        return ydb.OptionalType(ydb.PrimitiveType.Utf8)
    if isinstance(value, bool):
        return ydb.PrimitiveType.Bool
    if isinstance(value, int):
        return ydb.PrimitiveType.Int64
    if isinstance(value, float):
        return ydb.PrimitiveType.Double
    if isinstance(value, str):
        return ydb.PrimitiveType.Utf8
    if isinstance(value, bytes):
        return ydb.PrimitiveType.String
    if isinstance(value, UUID):
        return ydb.PrimitiveType.UUID
    if isinstance(value, Decimal):
        return ydb.DecimalType(22, 9)
    msg = f"Cannot infer YDB type for value {value!r} of type {type(value)}"
    raise ValueError(msg)


_TEMPORAL_VALUE_TYPES = (datetime, date, time, timedelta)
_TEMPORAL_FIELD_TYPES = frozenset(
    {"DateTimeField", "DateField", "DurationField", "TimeField"}
)


class _TypedParam:
    """
    A query parameter that already carries its YDB type. Subquery compilers
    return these so that parameters compose when a query is embedded in an
    enclosing query (the outermost query assigns the final placeholder names).
    """

    __slots__ = ("value", "ydb_type")

    def __init__(self, value, ydb_type):
        self.value = value
        self.ydb_type = ydb_type


def _resolve_one(field_type, val):
    # A non-temporal field type with a temporal value is a contradiction
    # (e.g. __year=N compares datetime bounds but its lookup's output_field is
    # IntegerField); trust the value in that case.
    if (
        field_type is not None
        and field_type not in _TEMPORAL_FIELD_TYPES
        and isinstance(val, _TEMPORAL_VALUE_TYPES)
    ):
        field_type = None

    if field_type == "DateTimeField":
        if isinstance(val, int):
            # An extract comparison (e.g. __month=1) whose left-hand side is a
            # DateTimeField but whose operand is an integer, not a timestamp.
            return (val, ydb.PrimitiveType.Int32)
        return (int(val.timestamp()), _ydb_types[field_type])
    if field_type in _ydb_types:
        return (val, _ydb_types[field_type])
    if isinstance(val, datetime):
        return (int(val.timestamp()), ydb.PrimitiveType.Datetime)
    if isinstance(val, date):
        return (val, ydb.PrimitiveType.Date)
    return (val, _infer_ydb_type(val))


def _resolve_typed_params(internal_types, params):
    # ``internal_types`` is aligned 1:1 with ``params``: the Django field
    # internal type for each parameter, or None when it could not be resolved
    # from the expression tree. Returns a list of (value, ydb_type). Parameters
    # produced by a subquery already carry their type and pass through.
    resolved = []
    for i, val in enumerate(params):
        if isinstance(val, _TypedParam):
            resolved.append((val.value, val.ydb_type))
        else:
            field_type = internal_types[i] if i < len(internal_types) else None
            resolved.append(_resolve_one(field_type, val))
    return resolved


def _generate_params_for_update(placeholder_rows, internal_types, params):
    resolved = _resolve_typed_params(internal_types, params)
    return {ph: resolved[i] for i, ph in enumerate(placeholder_rows)}


def _get_field_internal_type(field):
    if getattr(field, "remote_field", None) and hasattr(field, "target_field"):
        return field.target_field.get_internal_type()
    return field.get_internal_type()


def _get_data(fields, param_rows):
    result = []

    for i in range(len(param_rows)):
        struct = {}
        for j in range(len(fields)):
            val = param_rows[i][j]
            is_dt = _get_field_internal_type(fields[j]) == "DateTimeField"
            if is_dt and val is not None:
                struct[fields[j].column] = (
                    val if isinstance(val, int) else int(val.timestamp())
                )
            else:
                struct[fields[j].column] = val
        result.append(struct)

    return result


def _get_data_type(fields):
    struct_type = ydb.StructType()
    for f in fields:
        ydb_type = _ydb_types[_get_field_internal_type(f)]
        if getattr(f, "null", False):
            ydb_type = ydb.OptionalType(ydb_type)
        struct_type.add_member(f.column, ydb_type)
    return ydb.ListType(struct_type)


class SQLCompiler(_ParamTypingMixin, SQLCompiler):
    def get_order_by(self):
        result = super().get_order_by()
        # YDB rejects "ORDER BY N" (ordinal position reference, a Django 5.x
        # optimisation via PositionRef). Re-compile affected entries with the
        # underlying source expression so the actual column name is emitted.
        fixed = []
        for resolved, (o_sql, o_params, is_ref) in result:
            expr = getattr(resolved, "expression", None)
            is_position_ref = (
                expr is not None
                and hasattr(expr, "ordinal")
                and hasattr(expr, "source")
            )
            if is_position_ref:
                new_resolved = resolved.copy()
                new_resolved.set_source_expressions([expr.source])
                entry_sql, entry_params = self.compile(new_resolved)
            else:
                entry_sql, entry_params = o_sql, o_params
            fixed.append((resolved, (entry_sql, entry_params, is_ref)))
        return fixed

    def as_sql(self, with_limits=True, with_col_aliases=False):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.

        If 'with_limits' is False, any limit/offset information is not included
        in the query.
        """

        refcounts_before = self.query.alias_refcount.copy()
        # Per-parameter Django internal field types, kept aligned with ``params``.
        param_types = []
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
                param_types = [None] * len(params)
            elif self.qualify:
                result, params = self.get_qualify_sql()
                order_by = None
                param_types = [None] * len(params)
            else:
                distinct_fields, distinct_params = self.get_distinct()
                # This must come after 'select', 'ordering', and 'distinct'
                # (see docstring of get_from_clause() for details).
                from_, f_params = self.get_from_clause()
                try:
                    if self.where is not None:
                        where, w_params, w_types = self._compile_capturing(self.where)
                    else:
                        where, w_params, w_types = "", [], []
                except EmptyResultSet:
                    if self.elide_empty:
                        raise
                    # Use a predicate that's always False.
                    where, w_params, w_types = "0 = 1", [], []
                except FullResultSet:
                    where, w_params, w_types = "", [], []
                try:
                    if self.having is not None:
                        having, h_params, h_types = self._compile_capturing(
                            self.having
                        )
                    else:
                        having, h_params, h_types = "", [], []
                except FullResultSet:
                    having, h_params, h_types = "", [], []
                result = ["SELECT"]
                params = []

                if self.query.distinct:
                    distinct_result, distinct_params = self.connection.ops.distinct_sql(
                        distinct_fields,
                        distinct_params,
                    )
                    result += distinct_result
                    params += distinct_params
                    param_types += [None] * len(distinct_params)

                out_cols = []
                for _, (s_sql, s_params), alias in self.select + extra_select:
                    if alias:
                        s_sql = f"{s_sql} AS {self.connection.ops.quote_name(alias)}"  # noqa: PLW2901
                    params.extend(s_params)
                    param_types += [None] * len(s_params)
                    out_cols.append(s_sql)

                result += [", ".join(out_cols)]

                if from_:
                    result += ["FROM", *from_]
                elif self.connection.features.bare_select_suffix:
                    result += [self.connection.features.bare_select_suffix]
                params.extend(f_params)
                param_types += [None] * len(f_params)

                if where:
                    result.append(f"WHERE {where}")
                    params.extend(w_params)
                    param_types += w_types

                grouping = []
                for g_sql, g_params in group_by:
                    grouping.append(g_sql)
                    params.extend(g_params)
                    param_types += [None] * len(g_params)
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
                    param_types += h_types

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
                    param_types += [None] * len(o_params)
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
                sql = (
                    f"SELECT {', '.join(sub_selects)} "
                    f"FROM ({' '.join(result)}) subquery"
                )
                composed = _resolve_typed_params(
                    [], sub_params
                ) + _resolve_typed_params(param_types, params)
                return sql, [_TypedParam(v, t) for v, t in composed]

            sql = " ".join(result)
            resolved = _resolve_typed_params(param_types, params)
            if self.query.subquery:
                # Compose into the enclosing query: keep %s placeholders and
                # carry types; the outermost query names the placeholders.
                return sql, [_TypedParam(v, t) for v, t in resolved]

            sql, placeholder_rows = _replace_placeholders(sql)
            modified_params = {
                ph: resolved[i] for i, ph in enumerate(placeholder_rows)
            }

            return sql, modified_params
        finally:
            # Finally do cleanup - get rid of the joins we created above.
            self.query.reset_refcounts(refcounts_before)


class BaseSQLWriteCompiler(compiler.SQLInsertCompiler):
    def _prepare_sql_statement(self, returning_columns=None):
        qn = self.connection.ops.quote_name
        opts = self.query.get_meta()
        fields = self.query.fields or [opts.pk]

        field_types = []
        for f in fields:
            yql_type = self.connection.introspection.get_yql_type(
                _get_field_internal_type(f)
            )
            if getattr(f, "null", False):
                yql_type = f"Optional<{yql_type}>"
            field_types.append(f"{qn(f.column)}: {yql_type}")
        in_ = f"{', '.join(field_types)}"

        select = (
            f"SELECT {', '.join(qn(f.column) for f in fields)} FROM AS_TABLE($in_)"
        )
        if returning_columns:
            # YDB returns database-generated keys (Serial) in input row order.
            select += f" RETURNING {', '.join(qn(c) for c in returning_columns)}"

        return [
            f"DECLARE $in_ as List<Struct<{in_}>>;",
            f"{self._get_statement()} {qn(opts.db_table)}",
            f"({', '.join(qn(f.column) for f in fields)})",
            f"{select};",
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

    def as_sql(self, returning_columns=None):
        sql = self._prepare_sql_statement(returning_columns)
        params = self._prepare_params()
        return [(" ".join(sql), params)]

    def execute_sql(self, returning_fields=None):
        opts = self.query.get_meta()
        auto_pk = isinstance(
            opts.pk,
            (models.AutoField, models.SmallAutoField, models.BigAutoField),
        )
        if returning_fields is None and auto_pk:
            returning_fields = [opts.pk]

        # Read database-generated primary keys with RETURNING. When the PK is
        # supplied with the row (explicit value or non-auto PK) its value is
        # already known, so RETURNING is unnecessary.
        pk_supplied = bool(self.query.fields) and opts.pk in self.query.fields
        use_returning = bool(returning_fields) and auto_pk and not pk_supplied
        returning_columns = [opts.pk.column] if use_returning else None

        with self.connection.cursor() as cursor:
            returned = []
            for sql, params in self.as_sql(returning_columns):
                cursor.execute(sql, params)
                if use_returning and cursor.description:
                    returned = cursor.fetchall()

            if not returning_fields:
                return []

            if use_returning:
                rows = [tuple(row) for row in returned]
            else:
                # The PK is already known; echo it back from the inserted rows.
                rows = [
                    (self.pre_save_val(opts.pk, obj),) for obj in self.query.objs
                ]

            cols = [field.get_col(opts.db_table) for field in returning_fields]
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


class SQLDeleteCompiler(_ParamTypingMixin, compiler.SQLDeleteCompiler):
    def _as_sql(self, query):
        delete = f"DELETE FROM {self.quote_name_unless_alias(query.base_table)}"
        # RETURNING lets execute_sql count the deleted rows (YDB reports
        # cursor.rowcount == -1 for DELETE).
        returning = (
            f" RETURNING {self.quote_name_unless_alias(query.model._meta.pk.column)}"
        )

        try:
            where, params, param_types = self._compile_capturing(query.where)
        except FullResultSet:
            return delete + returning, ()
        sql, params = f"{delete} WHERE {where}{returning}", tuple(params)
        sql, placeholder_rows = _replace_placeholders(sql)

        modified_params = _generate_params_for_update(
            placeholder_rows, param_types, params
        )

        return sql, modified_params

    def execute_sql(self, result_type=compiler.MULTI, *args, **kwargs):
        cursor = super().execute_sql(result_type, *args, **kwargs)
        # Count the RETURNING rows so QuerySet.delete() reports a real number.
        if cursor is not None and getattr(cursor, "rowcount", 0) == -1:
            rows = cursor.fetchall() if cursor.description else []
            cursor.rowcount = len(rows)
        return cursor

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


class SQLUpdateCompiler(_ParamTypingMixin, compiler.SQLUpdateCompiler):
    def as_sql(self):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.
        """
        self.pre_sql_setup()
        if not self.query.values:
            return "", ()
        qn = self.quote_name_unless_alias
        values, update_params, set_types = [], [], []
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
                sub_sql, sub_params, sub_types = self._compile_capturing(val)
                values.append(f"{qn(name)} = {placeholder % sub_sql}")
                update_params.extend(sub_params)
                set_types += sub_types
            elif val is not None:
                values.append(f"{qn(name)} = {placeholder}")
                update_params.append(val)
                set_types.append(_get_field_internal_type(field))
            else:
                values.append(f"{qn(name)} = NULL")
        table = self.query.base_table

        result = [
            f"UPDATE {qn(table)} SET",
            ", ".join(values),
        ]

        try:
            where, where_params, where_types = self._compile_capturing(
                self.query.where
            )
        except FullResultSet:
            where_params, where_types = [], []
        else:
            result.append(f"WHERE {where}")

        # YDB does not report an affected-row count (cursor.rowcount is always
        # -1), but it does support RETURNING. Emit the primary key so the real
        # number of updated rows can be counted in execute_sql; this is what
        # Model.save() relies on to decide between UPDATE and INSERT.
        result.append(f"RETURNING {qn(self.query.model._meta.pk.column)}")

        sql, params = " ".join(result), tuple(update_params + where_params)
        param_types = set_types + where_types
        sql, placeholder_rows = _replace_placeholders(sql)

        modified_params = _generate_params_for_update(
            placeholder_rows, param_types, params
        )
        return sql, modified_params

    def execute_sql(self, returning_fields=None):
        """
        Execute the specified update. Return the number of rows affected by
        the primary update query, counted from the RETURNING result set so the
        ORM can correctly tell an updated row from a missing one.
        """
        self.returning_fields = returning_fields
        with self.connection.cursor() as cursor:
            sql, params = self.as_sql()
            if not sql:
                return 0
            cursor.execute(sql, params)
            rows = cursor.fetchall() if cursor.description else []
            return len(rows)


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
