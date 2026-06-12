"""
Smoke tests proving the standard Django contrib apps (admin, auth,
contenttypes, sessions) migrate and operate at the ORM level on YDB (issue
#40).

The contrib apps are installed in tests/settings.py, so a clean test-database
migrate already exercises their migrations. Each test creates its own data so
it does not depend on post_migrate fixtures surviving TransactionTestCase
flushes.
"""

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
