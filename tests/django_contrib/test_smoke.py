"""
Smoke tests proving the standard Django contrib apps (admin, auth,
contenttypes, sessions) migrate and operate at the ORM level on YDB (issue
#40).

The contrib apps are installed in tests/settings.py, so a clean test-database
migrate already exercises their migrations. Each test creates its own data so
it does not depend on post_migrate fixtures surviving TransactionTestCase
flushes.
"""

from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import connection
from django.test import Client
from django.test import TransactionTestCase


class TestContribSmoke(TransactionTestCase):
    databases = {"default"}

    def setUp(self):
        # django_content_type is flushed between TransactionTestCase tests, so
        # drop the manager cache to avoid handing out stale content type ids.
        ContentType.objects.clear_cache()

    def test_contrib_tables_migrated(self):
        tables = set(connection.introspection.table_names())
        for table in [
            "auth_user",
            "auth_group",
            "auth_permission",
            "auth_group_permissions",
            "auth_user_groups",
            "auth_user_user_permissions",
            "django_content_type",
            "django_admin_log",
            "django_session",
        ]:
            self.assertIn(table, tables)

    def test_create_user_and_superuser(self):
        User.objects.create_user("alice", "alice@example.com", "secret")
        root = User.objects.create_superuser("root", "root@example.com", "secret")

        self.assertTrue(
            User.objects.get(username="alice").check_password("secret")
        )
        self.assertTrue(root.is_staff)
        self.assertTrue(root.is_superuser)

    def test_group_membership_m2m(self):
        user = User.objects.create_user("bob", "bob@example.com", "secret")
        editors = Group.objects.create(name="editors")

        user.groups.add(editors)
        self.assertEqual(
            list(user.groups.values_list("name", flat=True)), ["editors"]
        )
        # Reverse accessor through the same auto-created table.
        self.assertTrue(editors.user_set.filter(pk=user.pk).exists())

        user.groups.remove(editors)
        self.assertEqual(user.groups.count(), 0)

    def test_permissions_and_contenttype(self):
        content_type = ContentType.objects.get_for_model(User)
        self.assertEqual(content_type.model, "user")

        permission = Permission.objects.create(
            codename="can_do_thing",
            name="Can do thing",
            content_type=content_type,
        )
        group = Group.objects.create(name="staff")
        group.permissions.add(permission)
        user = User.objects.create_user("carol", "carol@example.com", "secret")
        user.user_permissions.add(permission)

        self.assertEqual(group.permissions.count(), 1)
        self.assertEqual(user.user_permissions.count(), 1)

    def test_session_store_round_trip(self):
        session = SessionStore()
        session["user_id"] = 99
        session.create()

        loaded = SessionStore(session_key=session.session_key)
        self.assertEqual(loaded["user_id"], 99)

        session.delete()
        self.assertFalse(SessionStore().exists(session.session_key))

    def test_admin_login_and_index_urls(self):
        User.objects.create_superuser("admin", "admin@example.com", "secret")
        client = Client()

        self.assertTrue(client.login(username="admin", password="secret"))
        self.assertEqual(client.get("/admin/").status_code, 200)
        self.assertEqual(client.get("/admin/auth/user/").status_code, 200)
        self.assertEqual(client.get("/admin/auth/group/").status_code, 200)
        self.assertEqual(client.get("/admin/auth/user/?q=admin").status_code, 200)

    def test_uniqueness_not_enforced_at_db_level(self):
        # Documented limitation: YDB does not enforce unique constraints, so
        # paths that bypass Model.full_clean()/validate_unique (here a direct
        # create) can insert duplicate usernames. See docs/MIGRATIONS.md.
        User.objects.create(username="dup")
        User.objects.create(username="dup")
        self.assertEqual(User.objects.filter(username="dup").count(), 2)


class TestAdminAuthRelations(TransactionTestCase):
    """
    Relationship handling for Django Admin/Auth (issue #28). Relations are
    plain scalar ``*_id`` columns typed from the target primary key; these
    tests pin the behaviour that originally broke standard admin/auth usage.
    """

    databases = {"default"}

    def setUp(self):
        ContentType.objects.clear_cache()

    def test_permission_content_type_in_query(self):
        # Regression for #23: post_migrate create_permissions runs
        # Permission.objects.filter(content_type__in=ctypes).values_list(
        #     "content_type", "codename"), which raised IndexError in the SQL
        # compiler before relationship fields were typed as scalar *_id columns
        # and their params taken from the target field.
        user_ct = ContentType.objects.get_for_model(User)
        group_ct = ContentType.objects.get_for_model(Group)

        rows = set(
            Permission.objects.filter(
                content_type__in={user_ct, group_ct}
            ).values_list("content_type", "codename")
        )

        self.assertTrue(rows)
        self.assertTrue(all(ct in {user_ct.id, group_ct.id} for ct, _ in rows))

    def test_nullable_foreign_key_round_trip(self):
        # LogEntry.content_type is a nullable FK, so the scalar *_id column must
        # round-trip both a value and NULL.
        user = User.objects.create_superuser(
            "logger", "logger@example.com", "secret"
        )
        user_ct = ContentType.objects.get_for_model(User)

        with_ct = LogEntry.objects.create(
            user=user,
            content_type=user_ct,
            object_id="1",
            object_repr="obj",
            action_flag=ADDITION,
            change_message="created",
        )
        without_ct = LogEntry.objects.create(
            user=user,
            content_type=None,
            object_id=None,
            object_repr="none",
            action_flag=ADDITION,
            change_message="created",
        )

        self.assertEqual(
            LogEntry.objects.get(pk=with_ct.pk).content_type_id, user_ct.id
        )
        self.assertIsNone(LogEntry.objects.get(pk=without_ct.pk).content_type_id)

    def test_auth_user_nullability_matches_django(self):
        # On a clean schema the optional Django fields must be created nullable
        # (e.g. last_login) and the required ones NOT NULL (issue #28).
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor, "auth_user"
            )
        null_ok = {field.name: field.null_ok for field in description}

        self.assertTrue(null_ok["last_login"])
        self.assertFalse(null_ok["username"])


class TestAdminWrites(TransactionTestCase):
    databases = {"default"}

    def test_admin_create_change_delete_via_forms(self):
        # The admin write path (ModelForm POSTs) works end to end on YDB, using
        # the built-in Group admin (add / change / delete).
        User.objects.create_superuser("admin", "admin@example.com", "secret")
        client = Client()
        client.login(username="admin", password="secret")

        add = client.post(
            "/admin/auth/group/add/", {"name": "editors", "_save": "Save"}
        )
        self.assertIn(add.status_code, (200, 302))
        group = Group.objects.get(name="editors")

        client.post(
            f"/admin/auth/group/{group.pk}/change/",
            {"name": "writers", "_save": "Save"},
        )
        group.refresh_from_db()
        self.assertEqual(group.name, "writers")

        client.post(f"/admin/auth/group/{group.pk}/delete/", {"post": "yes"})
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())
