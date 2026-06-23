# Repository Guidelines

## Project Structure & Module Organization

`ydb_backend/` contains the Django database backend implementation. Backend integration points live in `ydb_backend/backend/`, while SQL compiler and manager extensions live under `ydb_backend/models/`. `tests/` contains the custom Django test suite, grouped by feature area such as `tests/compiler/`, `tests/type/`, and `tests/backends/ydb/`. `examples/bookstore/` is a runnable sample Django app. `docs/` holds Sphinx documentation sources and `docs/_static/` contains documentation assets.

## Build, Test, and Development Commands

- `poetry install --with docs`: install runtime, development, and documentation dependencies.
- `docker compose up`: start the local YDB service on ports `2136` and `8765`.
- `poetry run python tests/runtests.py`: run the full Django test suite against local YDB.
- `poetry run python tests/runtests.py compiler -v 2 --keepdb`: run one test module group with higher verbosity and preserve the test database.
- `poetry run ruff check ydb_backend tests`: lint source and tests.
- `poetry run ruff format ydb_backend tests`: format Python code.
- `cd docs && poetry run make html`: build Sphinx documentation.

## Coding Style & Naming Conventions

Use Python 3.10-compatible syntax and Ruff defaults from `pyproject.toml`: 88-character lines, single-line imports from Ruff isort, and four-space indentation. Keep public Django backend classes and methods aligned with Django naming conventions. Test files should follow `test_*.py`; model fixtures for a test area belong in that area’s `models.py`. Prefer explicit names for backend feature flags, compiler methods, and schema operations.

## Testing Guidelines

Tests use Django’s test runner through `tests/runtests.py`, not plain `pytest`. Start YDB before integration tests. Add tests near the behavior being changed, for example compiler SQL changes in `tests/compiler/` and type mapping changes in `tests/type/`. Keep assertions compatible with Django `TestCase` style; the Ruff config intentionally permits Django assert methods in tests.

## Commit & Pull Request Guidelines

Keep commits focused on one behavior or documentation change. Pull requests should include a concise summary, test commands run, and any YDB or Django compatibility notes. Link related issues when available and include screenshots only for documentation or example app UI changes. Every pull request must add a short, one-line entry to the top of `CHANGELOG.md` describing the change (a CI check enforces this); apply the `skip changelog` label for pull requests that need no entry, such as CI-only or docs-only changes.

## Security & Configuration Tips

Do not commit real YDB credentials or production database paths. Use local settings similar to the README example: `ENGINE = "ydb_backend.backend"`, `HOST = "localhost"`, `PORT = "2136"`, and `DATABASE = "/local"`.
