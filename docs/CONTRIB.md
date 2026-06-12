Django Admin, Auth, and contrib apps
===

The standard Django contrib applications — `django.contrib.admin`,
`django.contrib.auth`, `django.contrib.contenttypes`, and
`django.contrib.sessions` — run on YDB **with documented limitations**. They
migrate and operate at the ORM level, but the relational guarantees these apps
normally lean on are enforced by the application, not the database.

## Supported workflows

- `python manage.py migrate` for `admin`, `auth`, `contenttypes`, and
  `sessions` runs to completion (unenforceable constraints are skipped with a
  warning, see [MIGRATIONS](MIGRATIONS.md)).
- Creating users and superusers, checking passwords.
- Groups and permissions, including the `User.groups`,
  `User.user_permissions`, and `Group.permissions` many-to-many relations.
- Session create/load/delete round trips.
- Admin login and model changelists (for example `/admin/auth/user/`).

These workflows are covered by the smoke tests in
`tests/django_contrib/test_smoke.py`.

## How relations are stored

Relationship fields (`ForeignKey`, `OneToOneField`, `ManyToManyField`) are
stored as plain scalar `<name>_id` columns typed from the **target's primary
key**. No `FOREIGN KEY`, `REFERENCES`, or `ON DELETE` SQL is emitted. Querying a
relation by its scalar column — for example the
`Permission.objects.filter(content_type__in=...)` that Django runs after every
migrate — works because the parameter is typed from the related primary key.

Auto-created many-to-many through tables (such as `auth_user_groups`) are
created as ordinary YDB tables, so add/list/remove through the ORM works.

## Not enforced by the database (application responsibility)

YDB does not enforce these, so the application must:

- **Referential integrity** — a `*_id` value can point at a missing row.
- **Cascade deletes** — deleting a parent does not cascade at the database
  level (Django's ORM-level `on_delete` still runs for ORM deletes).
- **Uniqueness** — unique and `unique_together` constraints (including unique
  usernames and unique M2M pairs) are not enforced; rely on
  `Model.full_clean()` / `validate_unique()` and application logic. See
  [MIGRATIONS](MIGRATIONS.md) for how uniqueness is handled during migrate.

Nullable relationship and scalar columns round-trip correctly: an optional
`ForeignKey` stores either an id or `NULL`, and optional Django fields such as
`auth_user.last_login` are created nullable on a clean schema.
