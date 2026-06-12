"""Seed a bit of demo content so the contrib apps are visible out of the box.

Creates a flatpage at ``/about/`` and a redirect ``/home/`` -> ``/api/books/``.
This is example data, not schema; a real project would manage these through the
admin instead.
"""

from django.conf import settings
from django.db import migrations


def seed(apps, schema_editor):
    db = schema_editor.connection.alias
    Site = apps.get_model("sites", "Site")
    FlatPage = apps.get_model("flatpages", "FlatPage")
    Redirect = apps.get_model("redirects", "Redirect")

    # The default site is normally created by a post_migrate signal, which has
    # not run yet while migrations are applying, so ensure it exists.
    if not Site.objects.using(db).filter(pk=settings.SITE_ID).exists():
        Site.objects.using(db).create(
            pk=settings.SITE_ID, domain="localhost:8000", name="Bookstore"
        )
    site = Site.objects.using(db).get(pk=settings.SITE_ID)

    if not FlatPage.objects.using(db).filter(url="/about/").exists():
        about = FlatPage.objects.using(db).create(
            url="/about/",
            title="About this bookstore",
            content="<p>A Django + DRF demo running on the YDB backend.</p>",
        )
        about.sites.add(site)

    if not Redirect.objects.using(db).filter(
        site=site, old_path="/home/"
    ).exists():
        Redirect.objects.using(db).create(
            site=site, old_path="/home/", new_path="/api/books/"
        )


def unseed(apps, schema_editor):
    db = schema_editor.connection.alias
    FlatPage = apps.get_model("flatpages", "FlatPage")
    Redirect = apps.get_model("redirects", "Redirect")
    FlatPage.objects.using(db).filter(url="/about/").delete()
    Redirect.objects.using(db).filter(old_path="/home/").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0001_initial"),
        ("sites", "0001_initial"),
        ("flatpages", "0001_initial"),
        ("redirects", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
