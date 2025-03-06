from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    # An optional tuple indicating the minimum supported database version.
    minimum_database_version = (20,)
    allows_group_by_selected_pks = True
    update_can_self_select = False

    # Does the backend support self-reference subqueries in the DELETE
    # statement?
    delete_can_self_reference_subquery = False

    # Does the backend distinguish between '' and None?
    interprets_empty_strings_as_nulls = True

    # Does the backend allow inserting duplicate NULL rows in a nullable
    # unique field? All core backends implement this correctly, but other
    # databases such as SQL Server do not.
    supports_nullable_unique_constraints = False

    # Does the backend allow inserting duplicate rows when a unique_together
    # constraint exists and some fields are nullable but not all of them?
    supports_partially_nullable_unique_constraints = False

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
            "IPAddressField": "IPAddressField",
            "NullBooleanField": "NullBooleanField",
            "OneToOneField": "OneToOneField",
            "SlugField": "SlugField",
            "TextField": "TextField",
            "UUIDField": "UUIDField",
        }

    # Can the backend introspect the column order (ASC/DESC) for indexes?
    supports_index_column_ordering = False

    schema_editor_uses_clientside_param_binding = True

    # Does it support foreign keys?
    supports_foreign_keys = False

    # Can it create foreign key constraints inline when adding columns?
    can_create_inline_fk = False

    # Can an index be renamed?
    can_rename_index = False

    # Does it automatically index foreign keys?
    indexes_foreign_keys = False

    # Does it support CHECK constraints?
    supports_column_check_constraints = False
    supports_table_check_constraints = False

    # Does the backend support introspection of CHECK constraints?
    can_introspect_check_constraints = True

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

    # Does the backend support window expressions (expression OVER (...))?
    supports_over_clause = True
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
    # that should be skipped for this database.
    django_test_skips = {}

    supports_transactions = True
