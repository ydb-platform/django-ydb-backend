"""A runnable end-to-end workload for the bookstore example on YDB.

Unlike unit tests, this drives a real, full CRUD lifecycle across the app's own
models *and* the contrib apps it depends on (auth, sessions, sites, flatpages,
redirects), against the configured database. Use it to see — by hand or in a
demo — that a production-shaped Django app does real work on the YDB backend.

    python manage.py migrate          # once, to create the schema
    python manage.py workload          # run one pass
    python manage.py workload --count 20 --keep

Each created row is tagged with a per-run id and removed at the end (pass
``--keep`` to leave the data behind).
"""

from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.flatpages.models import FlatPage
from django.contrib.redirects.models import Redirect
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import transaction

from bookstore.models import Author
from bookstore.models import Book
from bookstore.models import Category

User = get_user_model()


class Command(BaseCommand):
    help = "Run a representative CRUD workload across the app and contrib apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=1, help="number of workload iterations"
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="keep the created rows instead of cleaning them up",
        )

    def handle(self, *args, **options):
        count = options["count"]
        keep = options["keep"]
        ops = 0
        for i in range(1, count + 1):
            tag = uuid4().hex[:8]
            self.stdout.write(self.style.MIGRATE_HEADING(f"iteration {i}/{count} ({tag})"))
            ops += self._app_models(tag, keep)
            ops += self._auth(tag, keep)
            ops += self._sessions(tag)
            ops += self._pages(tag, keep)
        self.stdout.write(
            self.style.SUCCESS(
                f"OK — {count} iteration(s), {ops} operations, no errors."
            )
        )

    # -- sections ---------------------------------------------------------

    def _app_models(self, tag, keep):
        # Create (FK + M2M), read, update, and delete the app's own models,
        # with one write wrapped in a transaction to exercise atomic().
        author = Author.objects.create(name=f"Author {tag}")
        category = Category.objects.create(name=f"Category {tag}")
        with transaction.atomic():
            book = Book.objects.create(
                title=f"Book {tag}",
                author=author,
                price=100,
                quantity=5,
                release_date="1972-01-01",
            )
            book.categories.add(category)

        assert Book.objects.get(pk=book.pk).author_id == author.pk
        assert Book.objects.filter(title__icontains=tag).count() == 1
        assert list(Book.objects.filter(author=author).order_by("price")) == [book]
        assert list(book.categories.all()) == [category]

        book.price = 250
        book.save(update_fields=["price"])
        assert Book.objects.get(pk=book.pk).price == 250

        book.categories.remove(category)
        assert book.categories.count() == 0

        self._ok("app models", "Author/Category/Book CRUD, FK, M2M, atomic()")
        if not keep:
            book.delete()
            author.delete()
            category.delete()
        return 12

    def _auth(self, tag, keep):
        # Users, groups, permissions (M2M) — the heart of contrib.
        user = User.objects.create_user(f"user-{tag}", password="workload-pw")
        group = Group.objects.create(name=f"group-{tag}")
        perm = Permission.objects.filter(
            content_type__app_label="bookstore"
        ).first()
        if perm is not None:
            group.permissions.add(perm)
        user.groups.add(group)

        assert user.groups.filter(pk=group.pk).exists()
        if perm is not None:
            assert group.permissions.filter(pk=perm.pk).exists()

        user.groups.remove(group)
        assert user.groups.count() == 0

        self._ok("auth", "User, Group, Permission, group/permission M2M")
        if not keep:
            group.delete()
            user.delete()
        return 6

    def _sessions(self, tag):
        # The DB session backend (session_key is the primary key).
        store = SessionStore()
        store["tag"] = tag
        store.save()
        key = store.session_key
        loaded = SessionStore(session_key=key)
        assert loaded.get("tag") == tag
        store.delete()
        assert not SessionStore().exists(key)
        self._ok("sessions", "DB session create / load / delete")
        return 3

    def _pages(self, tag, keep):
        # Site framework + DB-driven flat pages and redirects (FK + M2M to Site).
        site, _ = Site.objects.get_or_create(
            pk=settings.SITE_ID,
            defaults={"domain": "localhost:8000", "name": "Bookstore"},
        )
        flatpage = FlatPage.objects.create(
            url=f"/p-{tag}/", title=f"Page {tag}", content="<p>hi</p>"
        )
        flatpage.sites.add(site)
        redirect = Redirect.objects.create(
            site=site, old_path=f"/r-{tag}/", new_path="/api/books/"
        )

        assert FlatPage.objects.get(pk=flatpage.pk).sites.filter(pk=site.pk).exists()
        assert Redirect.objects.get(site=site, old_path=f"/r-{tag}/").pk == redirect.pk

        self._ok("pages", "Site, FlatPage (M2M), Redirect (FK)")
        if not keep:
            flatpage.delete()
            redirect.delete()
        return 4

    # -- helpers ----------------------------------------------------------

    def _ok(self, section, detail):
        self.stdout.write(f"  {self.style.SUCCESS('OK')}  {section:<11} {detail}")
