# Bookstore — a Django app on YDB

A small but realistic Django project that runs the standard **contrib stack**
(`admin`, `auth`, `sessions`, `contenttypes`, `sites`, `redirects`, `flatpages`)
and a token-authenticated **Django REST Framework** API on top of the YDB
backend. Use it to see a production-shaped app — relations, migrations, the
admin, and an authenticated API — working end to end on YDB.

What it exercises:

- **auth + admin** — users, groups, permissions, and the Django admin site.
- **Relations** — `Book → Author` (ForeignKey) and `Book ↔ Category`
  (ManyToMany, via an auto-created through table).
- **A REST API** — `ModelViewSet` with token auth, search, ordering, pagination.
- **sites / redirects / flatpages** — the site framework plus DB-driven
  redirects and flat pages.

> YDB does not enforce foreign-key or uniqueness constraints; referential
> integrity and `on_delete` are handled by Django's ORM. See the
> [compatibility notes](https://ydb-platform.github.io/django-ydb-backend/SUPPORT.html).

## Prerequisites

- Python 3.10+
- Docker and Docker Compose (for a local YDB)

## 1. Install dependencies

From the repository root:

```bash
poetry install
poetry run pip install djangorestframework   # only this example needs DRF
```

## 2. Start YDB

```bash
docker compose up -d --wait
```

This serves a local YDB at `localhost:2136`, database `/local` — the values the
example's settings already point at.

## 3. Apply migrations

From this directory (`examples/bookstore`):

```bash
poetry run python manage.py migrate
```

## 4. Run the workload (a quick end-to-end check)

Before starting the server, prove the whole stack does real work on YDB with the
bundled `workload` command. It runs a full create / read / update / delete cycle
across the app's models **and** the contrib apps (auth, sessions, sites,
flatpages, redirects), then cleans up after itself:

```bash
poetry run python manage.py workload
```

```text
iteration 1/1 (3f9c0a12)
  OK  app models  Author/Category/Book CRUD, FK, M2M, atomic()
  OK  auth        User, Group, Permission, group/permission M2M
  OK  sessions    DB session create / load / delete
  OK  pages       Site, FlatPage (M2M), Redirect (FK)
OK — 1 iteration(s), 25 operations, no errors.
```

Push more load through it, or keep the created rows, with `--count` / `--keep`:

```bash
poetry run python manage.py workload --count 50
```

## 5. Run the app

```bash
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
```

- Admin:         http://127.0.0.1:8000/admin/
- Browsable API: http://127.0.0.1:8000/api/

## API walkthrough

Authentication is token based: reads are public, writes require a token.

### Get a token

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<your-password>"}'
# -> {"token": "..."}

TOKEN=<token-from-above>
```

### Create an author, a category, and a book (ForeignKey + ManyToMany)

```bash
curl -X POST http://127.0.0.1:8000/api/authors/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Arkady & Boris Strugatsky"}'

curl -X POST http://127.0.0.1:8000/api/categories/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Science Fiction"}'

curl -X POST http://127.0.0.1:8000/api/books/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "title": "Roadside Picnic",
        "author": 1,
        "categories": [1],
        "price": 350,
        "quantity": 7,
        "limited_edition": true,
        "release_date": "1972-01-01"
      }'
```

### List, search, sort, paginate (public)

```bash
curl http://127.0.0.1:8000/api/books/
curl "http://127.0.0.1:8000/api/books/?search=Roadside"
curl "http://127.0.0.1:8000/api/books/?ordering=price"
curl "http://127.0.0.1:8000/api/books/?ordering=-price&page=2"
```

### Update and delete

```bash
curl -X PATCH http://127.0.0.1:8000/api/books/1/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"price": 400}'

curl -X DELETE http://127.0.0.1:8000/api/books/1/ \
  -H "Authorization: Token $TOKEN"
```

## Site framework, flat pages, and redirects

`migrate` seeds a little demo content (see
`bookstore/migrations/0002_demo_content.py`), so these work immediately:

```bash
# flat page served by FlatpageFallbackMiddleware
curl http://127.0.0.1:8000/about/

# redirect served by RedirectFallbackMiddleware (301 -> /api/books/)
curl -i http://127.0.0.1:8000/home/
```

Manage them in the admin under **Sites**, **Flat pages**, and **Redirects**.

## Where to go next

- **[Documentation](https://ydb-platform.github.io/django-ydb-backend/)** —
  configuration and authentication, fields, migrations, queries, transactions,
  and the native `UPSERT`.
- **[Compatibility and limitations](https://ydb-platform.github.io/django-ydb-backend/SUPPORT.html)**
  — what YDB does and does not enforce, and the supported version matrix.
