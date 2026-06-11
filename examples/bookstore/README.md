# Bookstore — Django + DRF on YDB

A small but realistic example that runs the **standard Django contrib stack**
(`admin`, `auth`, `sessions`, `contenttypes`) and a **modern Django REST
Framework API** on top of the YDB backend.

It exercises the things a real app needs:

- **auth + admin** — users, groups, permissions and the Django admin site.
- **Relations** — `Book → Author` (ForeignKey) and `Book ↔ Category`
  (ManyToMany, backed by an auto-created through table).
- **A token-authenticated REST API** — `ModelViewSet` + `DefaultRouter`,
  `IsAuthenticatedOrReadOnly`, search, ordering and pagination.
- **sites / redirects / flatpages** — the site framework plus DB-driven
  redirects and flat pages (FK + ManyToMany to `Site`).

> YDB has no foreign-key constraints; referential integrity and `on_delete`
> are handled by Django's ORM (see `docs/MIGRATIONS.md`).

## Setup

Start YDB (from the repository root):

```bash
docker compose up -d
```

Install dependencies. Django REST Framework is only needed for this example:

```bash
poetry install
poetry run pip install djangorestframework
```

## Run

From this directory (`examples/bookstore`):

```bash
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
```

- Admin:          http://127.0.0.1:8000/admin/
- Browsable API:  http://127.0.0.1:8000/api/

## API

Authentication is token based. Reads are public; writes require a token.

### Get a token

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<your-password>"}'
# -> {"token": "..."}
```

Export it for the calls below:

```bash
TOKEN=<token-from-above>
```

### Create an author and categories

```bash
curl -X POST http://127.0.0.1:8000/api/authors/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Arkady & Boris Strugatsky"}'

curl -X POST http://127.0.0.1:8000/api/categories/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Science Fiction"}'
```

### Create a book (ForeignKey + ManyToMany)

```bash
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

### List, search and sort (public)

```bash
curl http://127.0.0.1:8000/api/books/
curl "http://127.0.0.1:8000/api/books/?search=Roadside"
curl "http://127.0.0.1:8000/api/books/?ordering=price"
curl "http://127.0.0.1:8000/api/books/?ordering=-price&page=2"
```

### Retrieve / update / delete

```bash
curl http://127.0.0.1:8000/api/books/1/

curl -X PATCH http://127.0.0.1:8000/api/books/1/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"price": 400}'

curl -X DELETE http://127.0.0.1:8000/api/books/1/ \
  -H "Authorization: Token $TOKEN"
```

## Site framework, flat pages & redirects

`migrate` seeds a small amount of demo content (see
`bookstore/migrations/0002_demo_content.py`), so these work immediately:

```bash
# flat page served by FlatpageFallbackMiddleware
curl http://127.0.0.1:8000/about/

# redirect served by RedirectFallbackMiddleware (302/301 -> /api/books/)
curl -i http://127.0.0.1:8000/home/
```

Manage them in the admin under **Sites**, **Flat pages** and **Redirects**.
`FlatPage` has a ManyToMany to `Site` and `Redirect` a ForeignKey to `Site` —
both stored as plain columns and an auto-created through table (no FK
constraints; integrity is handled by Django).
