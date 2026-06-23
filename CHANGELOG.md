* docs: restructure the docs — add a quick start, move the support tables into each topic page, slim the compatibility page, and source the docs version from the package
* feat: native YDB `UPSERT INTO` for `YDBManager`
* feat: type query parameters from the expression tree
* feat: support `TimeField` and pre-1970 dates via YDB's wide signed date/time types
* feat: support `DecimalField` with arbitrary precision and scale
* feat: support `__hour`/`__minute`/`__second` lookups on `TimeField`
* feat: auto-created many-to-many through tables
* feat: accurate introspection and an explicit schema-operation boundary
* feat: covering indexes via the `COVER` clause
* feat: read auto-increment keys via `INSERT ... RETURNING`
* feat: map `Pi()`, `Random()`, `CURRENT_TIMESTAMP` and `Substr()` to YQL built-ins
* feat: add an SDK-policy retry helper for interactive transactions
* fix: correct LIKE/exact lookup escaping for YQL (`ESCAPE '~'`)
* fix: GROUP BY validation and `aggregate()` parameter binding
* fix: drop constant GROUP BY/ORDER BY terms and order by aggregate aliases
* fix: support a nullable expression right-hand side in pattern lookups
* fix: `bulk_update()` on NOT NULL columns and relation-chain types
* fix: compose UNION queries under the named-parameter model
* fix: resolve relation-conformance gaps in DELETE and `dates()`
* fix: raise `IntegrityError` on NOT NULL violations and reject primary-key-only inserts clearly
* fix: count UPDATE rows via RETURNING instead of a faked rowcount
* fix: apply NOT NULL -> nullable in `alter_field`
* fix: correct schema-editor `db_column` handling
* fix: emit a LIMIT before OFFSET for open-ended slices
* fix: audit and correct `DatabaseFeatures` flags
* docs: define the public support contract and compatibility matrices
* docs: define and verify the transaction/autocommit contract
* docs: modernize the bookstore example (DRF + Django contrib)
* test: gate on Django's bundled database suite across the 4.2/5.2/6.0 matrix
* test: add migration-executor, Django contrib, and Admin/Auth relationship tests
* ci: measure backend coverage and upload to Codecov
* ci: add key-value and transactional SLO workloads
* ci: require a short CHANGELOG.md entry on pull requests (skip via the 'skip changelog' label)

## 0.0.1b6 ##
* fix: support Optional<T> for nullable fields in insert and upsert
* fix: correct adapt_json_value and add JSONField tests

## 0.0.1b5 ##
* type DateTimeField extract params as Int32, not Datetime

## 0.0.1b4 ##
* One more db version case fixed

## 0.0.1b3 ##
* Fix supported db version check
* Fix relationship field parameter typing

## 0.0.1b1 ##
* Django YDB backend with basic functionality
