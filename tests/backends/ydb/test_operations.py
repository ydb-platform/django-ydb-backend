from django.core.management.color import no_style
from django.db import connection
from django.test import SimpleTestCase

from ..models import Person
from ..models import Tag

TZ_NAME = "Europe/Moscow"

LOOKUP_TYPES = [
    "like",
    "ilike",
    "regex",
    "iregex",
    "contains",
    "find",
    "startswith",
    "endswith",
    "istartswith",
    "iendswith",
]


class TestDatabaseOperations(SimpleTestCase):
    databases = {"default"}

    def test_format_for_duration_arithmetic(self):
        self.assertEqual(
            connection.ops.format_for_duration_arithmetic("column_name"),
            "DateTime::ToMicroseconds(column_name)",
        )
        self.assertEqual(
            connection.ops.format_for_duration_arithmetic(
                "Timestamp('2019-01-01T01:02:03.456789Z')"
            ),
            "DateTime::ToMicroseconds(Timestamp('2019-01-01T01:02:03.456789Z'))",
        )
        self.assertEqual(
            connection.ops.format_for_duration_arithmetic(""),
            "DateTime::ToMicroseconds()",
        )

    def test_extraction(self):
        sql_dt, params_dt = connection.ops.date_extract_sql("year", "column_name", [])
        sql_dttm, params_dttm = connection.ops.datetime_extract_sql(
            "hour", "column_name", [], tzname=None
        )

        self.assertEqual(sql_dt, "DateTime::GetYear(column_name)")
        self.assertEqual(sql_dttm, "DateTime::GetHour(column_name)")
        self.assertListEqual(params_dt, [])

    def test_trunc(self):
        sql_dt, params_dt = connection.ops.date_trunc_sql("year", "column_name", [])
        sql_dttm, params_dttm = connection.ops.datetime_trunc_sql(
            "hour", "column_name", [], tzname=TZ_NAME
        )

        self.assertEqual(sql_dt, "DateTime::StartOfYear(column_name)")
        self.assertEqual(
            sql_dttm,
            "DateTime::StartOf((AddTimezone(column_name, 'Europe/Moscow')), "
            "Interval('PT1H'))",
        )
        self.assertListEqual(params_dt, [])

    def test_datetime_cast_date_and_time_sql(self):
        sql_dt, params = connection.ops.datetime_cast_date_sql(
            "DateTime::MakeDatetime(DateTime::StartOfQuarter(Datetime('2019-06-06T01:02:03Z')))",
            [],
            TZ_NAME,
        )

        sql_tm, params = connection.ops.datetime_cast_time_sql(
            "DateTime::MakeDatetime(DateTime::StartOfQuarter(Datetime('2019-06-06T01:02:03Z')))",
            [],
            TZ_NAME,
        )
        self.assertEqual(
            sql_dt,
            "cast(AddTimezone(DateTime::MakeDatetime("
            "DateTime::StartOfQuarter(Datetime('2019-06-06T01:02:03Z'))), "
            "'Europe/Moscow') as date)",
        )

        self.assertEqual(
            sql_tm,
            "DateTime::Format('%H:%M:%S %Z')"
            "(AddTimezone(DateTime::MakeDatetime"
            "(DateTime::StartOfQuarter(Datetime('2019-06-06T01:02:03Z'))), "
            "'Europe/Moscow'))",
        )
        self.assertListEqual(params, [])

    def test_quote_name(self):
        self.assertEqual(connection.ops.quote_name("table_name"), "`table_name`")
        self.assertEqual(connection.ops.quote_name("`table_name`"), "`table_name`")
        self.assertEqual(
            connection.ops.quote_name("table name with  spaces"),
            "`table name with  spaces`",
        )
        self.assertEqual(connection.ops.quote_name("table-name"), "`table-name`")
        self.assertEqual(connection.ops.quote_name("table.name"), "`table.name`")
        self.assertEqual(connection.ops.quote_name("table_name!"), "`table_name!`")

    def test_regex_lookup(self):
        self.assertEqual(connection.ops.regex_lookup("regex"), "%s REGEXP %s")
        self.assertEqual(
            connection.ops.regex_lookup("iregex"),
            "Unicode::ToLower(%s) REGEXP Unicode::ToLower(%s)",
        )
        with self.assertRaises(NotImplementedError):
            connection.ops.regex_lookup("invalid_type")

    def test_lookup_cast(self):
        for lookup in LOOKUP_TYPES:
            with self.subTest(lookup=lookup):
                self.assertIn("optional<string>", connection.ops.lookup_cast(lookup))

    def test_prepare_sql_script(self):
        sql_script = """
        SELECT * FROM users;
        UPDATE users SET active = TRUE WHERE id = 1;
        DELETE FROM users WHERE id = 2;
        """

        expected_result = [
            "SELECT * FROM users;",
            "UPDATE users SET active = TRUE WHERE id = 1;",
            "DELETE FROM users WHERE id = 2;",
        ]

        result = connection.ops.prepare_sql_script(sql_script)
        self.assertEqual(result, expected_result)

    def test_sql_flush(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
            ),
            [
                "DELETE FROM `backends_person`;",
                "DELETE FROM `backends_tag`;",
            ],
        )

    def test_last_insert_id(self):
        with connection.cursor() as cursor:
            cursor.execute_scheme(
                "INSERT INTO `backends_tag` (name) VALUES ('Test Name');"
            )

            last_id = connection.ops.last_insert_id(cursor, "backends_tag", "id")
            self.assertIsInstance(last_id, int)
            self.assertTrue(last_id > 0)

    # def test_last_executed_query(self):
    #     # last_executed_query() interpolate all parameters, in most cases it is
    #     # not equal to QuerySet.query.
    #     for qs in (
    #         Article.objects.filter(pk=1),
    #         Article.objects.filter(pk__in=(1, 2), reporter__pk=3),
    #         Article.objects.filter(
    #             pk=1,
    #             reporter__pk=9,
    #         ).exclude(reporter__pk__in=[2, 1]),
    #         Article.objects.filter(pk__in=list(range(20, 31))),
    #     ):
    #         sql, params = qs.query.sql_with_params()
    #         with qs.query.get_compiler(DEFAULT_DB_ALIAS)\
    #                 .execute_sql(CURSOR) as cursor:
    #             self.assertEqual(
    #                 cursor.db.ops.last_executed_query(cursor, sql, params),
    #                 str(qs.query),
    #             )
    #
    # @skipUnlessDBFeature("supports_paramstyle_pyformat")
    # def test_last_executed_query_dict(self):
    #     square_opts = Square._meta
    #     sql = "INSERT INTO %s (%s, %s) VALUES" % (
    #         connection.introspection.identifier_converter(square_opts.db_table),
    #         connection.ops.quote_name(square_opts.get_field("root").column),
    #         connection.ops.quote_name(square_opts.get_field("square").column),
    #     )
    #     with connection.cursor() as cursor:
    #         params = [(2, 4)]
    #         cursor.execute(sql, params)
    #         self.assertEqual(
    #             cursor.db.ops.last_executed_query(cursor, sql, params),
    #             "%s %s" % (sql, ", ".join(map(str, params))),
    #         )
    #
    # @skipUnlessDBFeature("supports_paramstyle_pyformat")
    # def test_last_executed_query_params_dict(self):
    #     square_opts = Square._meta
    #     sql = "SELECT %s, %s FROM %s WHERE %s =" % (
    #         connection.ops.quote_name(square_opts.get_field("root").column),
    #         connection.ops.quote_name(square_opts.get_field("square").column),
    #         connection.introspection.identifier_converter(square_opts.db_table),
    #         connection.ops.quote_name(square_opts.get_field("root").column),
    #     )
    #     sql_with_param = f"{sql} %(root)s"
    #     with connection.cursor() as cursor:
    #         param_value = 2
    #         params = {"root": param_value}
    #         cursor.execute(sql_with_param, params)
    #         self.assertEqual(
    #             cursor.db.ops.last_executed_query(cursor, sql_with_param, params),
    #             "%s %s" % (sql, param_value),
    #         )
