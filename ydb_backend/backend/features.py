from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    # An optional tuple indicating the minimum supported database version.
    minimum_database_version = (20,)
    # YDB has no functional-dependency GROUP BY: every selected non-aggregated
    # column must appear in GROUP BY, so Django cannot group by the primary key
    # alone while selecting its other columns.
    allows_group_by_selected_pks = False
    # YDB rejects "GROUP BY 1" (ordinal reference) as a constant expression.
    allows_group_by_select_index = False
    update_can_self_select = False

    # Does the backend support self-reference subqueries in the DELETE
    # statement?
    delete_can_self_reference_subquery = False

    # Does the backend distinguish between '' and None?
    interprets_empty_strings_as_nulls = False

    # Does the backend consider table names with different casing to
    # be equal?
    ignores_table_name_case = True

    # Does the backend allow inserting duplicate NULL rows in a nullable
    # unique field? All core backend implement this correctly, but other
    # databases such as SQL Server do not.
    supports_nullable_unique_constraints = False

    # Does the backend allow inserting duplicate rows when a unique_together
    # constraint exists and some fields are nullable but not all of them?
    supports_partially_nullable_unique_constraints = False

    # YDB returns Serial keys via INSERT ... RETURNING (in input row order),
    # so bulk_create can read back generated primary keys safely.
    can_return_rows_from_bulk_insert = True
    uses_savepoints = False

    # Can a fixture contain forward references? i.e., are
    # FK constraints checked at the end of transaction, or
    # at the end of each save operation?
    supports_forward_references = False

    # Is there a true datatype for uuid?
    has_native_uuid_field = True

    # Is there a true datatype for timedeltas?
    has_native_duration_field = True

    # Does the database driver supports same type temporal data subtraction
    # by returning the type used to store duration field?
    supports_temporal_subtraction = True

    # Does the __regex lookup support backreferencing and grouping?
    supports_regex_backreferencing = False

    # Does the database have a copy of the zoneinfo database?
    has_zoneinfo_database = False

    # Does the backend support NULLS FIRST and NULLS LAST in ORDER BY?
    supports_order_by_nulls_modifier = False

    # Can an object have an autoincrement primary key of 0?
    allows_auto_pk_0 = False

    # Does the backend reset sequences between tests?
    supports_sequence_reset = False

    # Can the backend introspect the default value of a column?
    can_introspect_default = False

    # Confirm support for introspected foreign keys
    # Every database can do this reliably, except MySQL,
    # which can't do it for MyISAM tables
    can_introspect_foreign_keys = False

    # Map fields which some backend may not be able to differentiate to the
    # field it's introspected as.
    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            "DateField": "DateField",
            "DateTimeField": "DateTimeField",
            "DecimalField": "DecimalField",
            "FileField": "FileField",
            "FilePathField": "FilePathField",
            "FloatField": "FloatField",
            "DoubleField": "DoubleField",
            "IPAddressField": "IPAddressField",
            "NullBooleanField": "NullBooleanField",
            "SlugField": "SlugField",
            "TextField": "TextField",
            "UUIDField": "UUIDField",
            "EnumField": "EnumField",
            "EmailField": "EmailField",
        }

    # Can the backend introspect the column order (ASC/DESC) for indexes?
    supports_index_column_ordering = False

    schema_editor_uses_clientside_param_binding = True

    # Does it support foreign keys?
    supports_foreign_keys = False

    # Can it create foreign key constraints inline when adding columns?
    can_create_inline_fk = False

    # Can an index be renamed?
    can_rename_index = True

    # Does it automatically index foreign keys?
    indexes_foreign_keys = False

    # Does it support CHECK constraints?
    supports_column_check_constraints = False
    supports_table_check_constraints = False

    # YDB does not support CHECK constraints, so there is nothing to introspect.
    can_introspect_check_constraints = False

    # Does the backend support functions in defaults?
    supports_expression_defaults = False

    # Does the backend support the DEFAULT keyword in insert queries?
    supports_default_keyword_in_insert = False

    # Does the backend support the DEFAULT keyword in bulk insert queries?
    supports_default_keyword_in_bulk_insert = False

    # Does the backend support "select for update" queries with limit (and offset)?
    supports_select_for_update_with_limit = False

    # Combinatorial flags
    supports_select_intersection = False
    supports_select_difference = False
    supports_parentheses_in_compound = False
    requires_compound_order_by_subquery = False

    # YQL has a native XOR operator, so Django emits "a XOR b" directly rather
    # than the MOD()-based emulation (YDB has no MOD() builtin).
    supports_logical_xor = True

    # Does the backend support window expressions (expression OVER (...))?
    supports_over_clause = True
    # YDB supports ROWS BETWEEN N PRECEDING/FOLLOWING, but RANGE with bounded
    # offsets (RANGE BETWEEN N PRECEDING AND ...) is not supported.
    only_supports_unbounded_with_preceding_and_following = True

    # SQL to create a table with a composite primary key for use by the Django
    # test suite.
    create_test_table_with_composite_primary_key = """
            CREATE TABLE test_table_composite_pk (
                column_1 Int32 NOT NULL,
                column_2 Int32 NOT NULL,
                PRIMARY KEY(column_1, column_2)
            )
        """

    # Does the backend support ignoring constraint or uniqueness errors during
    # INSERT?
    supports_ignore_conflicts = False

    # Does the backend support partial indexes (CREATE INDEX ... WHERE ...)?
    supports_partial_indexes = False
    supports_functions_in_partial_indexes = False

    # Does the backend support covering indexes (CREATE INDEX ... INCLUDE ...)?
    supports_covering_indexes = True

    # Does the backend support indexes on expressions?
    supports_expression_indexes = False

    # Does the database allow more than one constraint or index on the same
    # field(s)?
    allows_multiple_constraints_on_same_fields = False

    # Can the backend introspect a JSONField?
    can_introspect_json_field = False

    # Is there a true datatype for JSON?
    has_native_json_field = True

    # Does value__d__contains={'f': 'g'} (without a list around the dict) match
    # {'d': [{'f': 'g'}]}?
    json_key_contains_list_matching_requires_list = True

    # Does the backend support JSONObject() database function?
    has_json_object_function = False

    # Does the backend support column collations?
    supports_collation_on_charfield = False
    supports_collation_on_textfield = False
    # Does the backend support non-deterministic collations?
    supports_non_deterministic_collations = False

    # SQL template override for tests.aggregation.tests.NowUTC
    test_now_utc_template = "CurrentUtcTimestamp()"

    # SQL to create a model instance using the database defaults.
    insert_test_table_with_defaults = "INSERT INTO {} DEFAULT VALUES;"

    # A set of dotted paths to tests in Django's test suite that are expected
    # to fail on this database.
    django_test_expected_failures = set()

    # A map of reasons to sets of dotted paths to tests in Django's test suite
    # that should be skipped for this database. Populated while triaging the
    # bundled Django suite via the conformance harness (issue #72); entries are
    # inert for this project's own test suite because the guarded test apps are
    # not in its INSTALLED_APPS.
    django_test_skips = {
        "Saving a model whose primary key has a database default issues a "
        "different number of queries on YDB (INSERT ... RETURNING).": {
            "basic.tests.ModelInstanceCreationTests."
            "test_save_parent_primary_with_default",
        },
        "select-on-save with an update that matches no rows raises instead of "
        "falling back to INSERT.": {
            "basic.tests.SelectOnSaveTests.test_select_on_save_lying_update",
        },
        # --- lookup module (issue #72), grouped by observed failure mode. ---
        # All four use OuterRef inside Exists/Subquery: the subquery references
        # the outer row, which YDB cannot resolve ("Member not found: <table>").
        # Correlated subqueries are a YDB platform limitation, not a parameter
        # wiring bug (issue #77; see docs/SUPPORT.md). Non-correlated subqueries
        # work.
        "Correlated subqueries (OuterRef inside Exists/Subquery, or an Exists/"
        "subquery as a lookup left-hand side) are unsupported by YDB.": {
            "lookup.tests.LookupQueryingTests.test_filter_exists_lhs",
            "lookup.tests.LookupQueryingTests.test_filter_subquery_lhs",
            "lookup.tests.LookupTests.test_exact_exists",
            "lookup.tests.LookupTests.test_nested_outerref_lhs",
        },
        "Lookups that coerce a value to a different field type (int-as-str, "
        "date-as-str) or apply regex to non-string/NULL operands raise during "
        "parameter handling.": {
            "lookup.tests.LookupTests.test_lookup_int_as_str",
            "lookup.tests.LookupTests.test_lookup_date_as_str",
            "lookup.tests.LookupTests.test_regex_non_string",
            "lookup.tests.LookupTests.test_regex_null",
        },
        "YDB GROUP BY validation rejects the SQL Django emits for these "
        "aggregate/decimal lookup queries.": {
            "lookup.test_decimalfield.DecimalFieldLookupTests.test_gt",
            "lookup.test_decimalfield.DecimalFieldLookupTests.test_gte",
            "lookup.test_decimalfield.DecimalFieldLookupTests.test_lt",
            "lookup.test_decimalfield.DecimalFieldLookupTests.test_lte",
            "lookup.tests.LookupQueryingTests.test_aggregate_combined_lookup",
        },
        "exclude()/values()/none()/__in projections return incorrect results "
        "or raise in the compiler.": {
            "lookup.tests.LookupTests.test_exclude",
            "lookup.tests.LookupTests.test_values",
            "lookup.tests.LookupTests.test_none",
            "lookup.tests.LookupTests.test_in_keeps_value_ordering",
            "lookup.tests.LookupTests.test_lookup_collision",
        },
        # --- queries module (issue #72). Plain union() now works; these are
        #     the remaining combinator sub-features. ---
        "ORDER BY / values_list ordering on a UNION result is not yet handled "
        "correctly.": {
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_ordering_by_alias",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_ordering_by_f_expression_and_alias",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_order_raises_on_non_selected_column",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_with_values_list_and_order",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_with_values_list_and_order_on_annotation",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_with_values_list_on_annotated_and_unannotated",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_multiple_models_with_values_list_and_order",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_multiple_models_with_values_list_and_order_by_extra_select",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_with_two_annotated_values_list",
        },
        "A UNION used as a subquery / with OuterRef, or wrapped for COUNT, "
        "still generates invalid SQL.": {
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_in_subquery",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_union_in_subquery_related_outerref",
            "queries.test_qs_combinators.QuerySetSetOperationTests."
            "test_count_union",
        },
        "bulk_update() works but issues a different number of queries on YDB "
        "(extra INSERT ... RETURNING round-trips), failing assertNumQueries.": {
            "queries.test_bulk_update.BulkUpdateNoteTests.test_simple",
            "queries.test_bulk_update.BulkUpdateNoteTests.test_multiple_fields",
            "queries.test_bulk_update.BulkUpdateNoteTests.test_batch_size",
            "queries.test_bulk_update.BulkUpdateNoteTests."
            "test_foreign_keys_do_not_lookup",
        },
        "bulk_update() with database functions, JSONField, or multi-table "
        "inheritance is not fully supported.": {
            "queries.test_bulk_update.BulkUpdateNoteTests.test_functions",
            "queries.test_bulk_update.BulkUpdateTests.test_json_field",
            "queries.test_bulk_update.BulkUpdateTests.test_inherited_fields",
        },
        "Requires multiple configured databases (database routing).": {
            "queries.test_bulk_update.BulkUpdateTests.test_database_routing",
            "queries.test_bulk_update.BulkUpdateTests."
            "test_database_routing_batch_atomicity",
        },
        "Inserting a model that has only an auto primary key (no other "
        "insertable fields) is not supported (raises NotSupportedError); "
        "QuerySet.contains()'s fixtures create such rows.": {
            "queries.test_contains.ContainsTests.test_basic",
            "queries.test_contains.ContainsTests.test_evaluated_queryset",
            "queries.test_contains.ContainsTests.test_obj_type",
            "queries.test_contains.ContainsTests.test_proxy_model",
            "queries.test_contains.ContainsTests.test_unsaved_obj",
            "queries.test_contains.ContainsTests.test_values",
            "queries.test_contains.ContainsTests.test_wrong_model",
        },
        # --- relation modules (issue #74 conformance expansion). ---
        "YDB does not enforce uniqueness, so creating a duplicate OneToOne does "
        "not raise IntegrityError (uniqueness is an application responsibility).": {
            "one_to_one.tests.OneToOneTests.test_multiple_o2o",
        },
        # Reproduced on the latest local-ydb:trunk only (the 2026-06-08 trunk
        # was green); the through-row INSERT inside set()'s atomic() is not
        # visible afterward. Normal transactional inserts are unaffected.
        "m2m set() with a through model loses the write on the latest YDB "
        "trunk (a transaction-visibility regression, not a backend bug); see "
        "issue #96.": {
            "m2m_through.tests.M2mThroughTests."
            "test_set_on_m2m_with_intermediate_model_value_required",
            "m2m_through.tests.M2mThroughReferentialTests."
            "test_set_on_symmetrical_m2m_with_intermediate_model",
        },
        # --- #72 conformance gate expansion (relations, CRUD, data; 2026-06-19). ---
        "Correlated subqueries (OuterRef in Exists/Subquery) are unsupported.": {
            "foreign_object.tests.MultiColumnFKTests.test_double_nested_query",
            "foreign_object.tests.MultiColumnFKTests."
            "test_forward_in_lookup_filters_correctly",
            "many_to_many.tests.ManyToManyTests.test_selects",
            "queryset_pickle.tests.PickleabilityTestCase."
            "test_pickle_boolean_expression_in_Q__queryset",
            "queryset_pickle.tests.PickleabilityTestCase."
            "test_pickle_exists_kwargs_queryset_not_evaluated",
            "queryset_pickle.tests.PickleabilityTestCase."
            "test_pickle_exists_queryset_not_evaluated",
            "queryset_pickle.tests.PickleabilityTestCase."
            "test_pickle_exists_queryset_still_usable",
            "queryset_pickle.tests.PickleabilityTestCase."
            "test_pickle_subquery_queryset_not_evaluated",
        },
        "Non-equi JOIN ON (composite-FK/FilteredRelation); YDB needs equi-join.": {
            "foreign_object.test_empty_join.RestrictedConditionsTests."
            "test_restrictions_with_no_joining_columns",
            "foreign_object.tests.MultiColumnFKTests.test_inheritance",
            "foreign_object.tests.MultiColumnFKTests.test_translations",
            "foreign_object.tests.TestExtraJoinFilterQ.test_extra_join_filter_q",
            "queryset_pickle.tests.PickleabilityTestCase.test_pickle_filteredrelation",
            "queryset_pickle.tests.PickleabilityTestCase."
            "test_pickle_filteredrelation_m2m",
        },
        "Different query count on YDB (INSERT ... RETURNING); assertNumQueries.": {
            "bulk_create.tests.BulkCreateTests.test_efficiency",
            "bulk_create.tests.BulkCreateTests.test_explicit_batch_size_efficiency",
            "bulk_create.tests.BulkCreateTests."
            "test_explicit_batch_size_respects_max_batch_size",
            "bulk_create.tests.BulkCreateTests.test_non_auto_increment_pk_efficiency",
            "bulk_create.tests.BulkCreateTests.test_set_pk_and_insert_single_item",
            "bulk_create.tests.BulkCreateTests.test_set_pk_and_query_efficiency",
            "many_to_many.tests.ManyToManyTests.test_add_existing_different_type",
            "many_to_one_null.tests.ManyToOneNullTests.test_set_clear_non_bulk",
            "order_with_respect_to.tests.OrderWithRespectToBaseTests."
            "test_database_routing",
            "update_only_fields.tests.UpdateOnlyFieldsTests."
            "test_num_queries_inheritance",
            "update_only_fields.tests.UpdateOnlyFieldsTests."
            "test_update_fields_fk_defer",
            "update_only_fields.tests.UpdateOnlyFieldsTests."
            "test_update_fields_inheritance",
            "update_only_fields.tests.UpdateOnlyFieldsTests."
            "test_update_fields_inheritance_defer",
        },
        "Unsupported on YDB (issue #72 conformance triage).": {
            "bulk_create.tests.BulkCreateTests.test_bulk_insert_expressions",
            "bulk_create.tests.BulkCreateTests.test_zero_as_autoval",
            "indexes.tests.CoveringIndexTests.test_covering_index",
            "indexes.tests.CoveringIndexTests.test_covering_partial_index",
            "model_regress.tests.ModelTests."
            "test_sql_insert_compiler_return_id_attribute",
            "update.tests.AdvancedTests.test_update_negated_f_conditional_annotation",
            "update.tests.SimpleTest.test_nonempty_update_with_inheritance",
        },
        "Insert of a column-less row (auto-PK-only/MTI parent) is unsupported.": {
            "bulk_create.tests.BulkCreateTests.test_bulk_insert_nullable_fields",
            "bulk_create.tests.BulkCreateTests.test_empty_model",
            "bulk_create.tests.BulkCreateTests.test_nullable_fk_after_parent",
            "bulk_create.tests.BulkCreateTests."
            "test_nullable_fk_after_parent_bulk_create",
            "custom_pk.tests.CustomPKTests.test_auto_field_subclass_bulk_create",
            "custom_pk.tests.CustomPKTests.test_auto_field_subclass_create",
            "defer.tests.DeferTests.test_defer_of_overridden_scalar",
            "m2m_and_m2o.tests.RelatedObjectUnicodeTests."
            "test_m2m_with_unicode_reference",
            "m2m_regress.tests.M2MRegressionTests.test_multiple_forwards_only_m2m",
            "many_to_many.tests.ManyToManyTests.test_inherited_models_selects",
            "null_queries.tests.NullQueriesTests.test_reverse_relations",
            "order_with_respect_to.tests.TestOrderWithRespectToOneToOnePK."
            "test_set_order",
        },
        "Custom transform emits raw SQL (UPPER/modulo) that YQL rejects.": {
            "custom_lookups.tests.BilateralTransformTests.test_bilateral_multi_value",
            "custom_lookups.tests.BilateralTransformTests.test_bilateral_order",
            "custom_lookups.tests.BilateralTransformTests.test_bilateral_upper",
            "custom_lookups.tests.BilateralTransformTests.test_div3_bilateral_extract",
            "custom_lookups.tests.LookupTests.test_basic_lookup",
            "custom_lookups.tests.LookupTests.test_div3_extract",
            "custom_lookups.tests.SubqueryTransformTests.test_subquery_usage",
        },
        "Requires savepoints (nested atomic), which YDB lacks.": {
            "get_or_create.tests.GetOrCreateTestsWithManualPKs.test_savepoint_rollback",
        },
        "Asserts backend-specific SQL text that differs on YDB.": {
            "custom_lookups.tests.YearLteTests.test_postgres_year_exact",
            "custom_lookups.tests.YearLteTests.test_year_lte_sql",
        },
        "YDB does not enforce uniqueness; expected IntegrityError not raised.": {
            "get_or_create.tests.GetOrCreateThroughManyToMany.test_something",
            "get_or_create.tests.UpdateOrCreateTests.test_integrity",
            "get_or_create.tests.UpdateOrCreateTests.test_manual_primary_key_test",
            "get_or_create.tests.UpdateOrCreateTestsWithManualPKs."
            "test_create_with_duplicate_primary_key",
        },
        "Generated YQL rejected by the server (unsupported construct).": {
            "custom_lookups.tests.BilateralTransformTests.test_transform_order_by",
            "extra_regress.tests.ExtraRegressTests.test_regression_8039",
            "ordering.tests.OrderingTests.test_order_by_constant_value",
            "ordering.tests.OrderingTests.test_orders_nulls_first_on_filtered_subquery",
        },
        # --- Django 5.2/6.0-only failures (#72 cross-version triage). ---
        "Multi-table-inheritance saves run as TransactionTestCase (YDB has no "
        "savepoints), so assertNumQueries also counts the per-save BEGIN/COMMIT.": {
            "force_insert_update.tests.ForceInsertInheritanceTests."
            "test_force_insert_diamond_mti",
            "force_insert_update.tests.ForceInsertInheritanceTests."
            "test_force_insert_false",
            "force_insert_update.tests.ForceInsertInheritanceTests."
            "test_force_insert_false_with_existing_parent",
            "force_insert_update.tests.ForceInsertInheritanceTests."
            "test_force_insert_parent",
            "force_insert_update.tests.ForceInsertInheritanceTests."
            "test_force_insert_with_existing_grandparent",
            "force_insert_update.tests.ForceInsertInheritanceTests."
            "test_force_insert_with_grandparent",
        },
        "YDB's IN rejects a multi-column subquery source, so composite-key "
        "tuple lookups (a, b) IN (subquery) are unsupported.": {
            "foreign_object.test_tuple_lookups.TupleLookupsTests."
            "test_in_subquery",
            "foreign_object.test_tuple_lookups.TupleLookupsTests."
            "test_tuple_in_subquery",
        },
        "YDB forbids '.' in a column name, and rejects ORDER BY a constant "
        "expression.": {
            "ordering.tests.OrderingTests."
            "test_alias_with_period_shadows_table_name",
            "ordering.tests.OrderingTests.test_order_by_case_when_constant_value",
        },
        "The test's custom lookup concatenates lhs_params + rhs_params assuming "
        "both are lists; YDB returns subquery params as a tuple (the test itself "
        "notes the resilient (*lhs, *rhs) form).": {
            "custom_lookups.tests.LookupTests.test_custom_lookup_with_subquery",
        },
    }

    supports_transactions = True
