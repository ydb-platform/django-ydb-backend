from pathlib import Path

BASE_DIR = Path(__file__).parent

SECRET_KEY = "django-insecure-test-key"  # noqa: S105
USE_TZ = True
ALLOWED_HOSTS = ["testserver", "localhost"]
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
ROOT_URLCONF = "urls"

# Standard Django contrib apps are installed so the contrib smoke tests
# (tests/django_contrib) can migrate and exercise admin/auth/sessions. Feature
# test modules are appended to INSTALLED_APPS by runtests.py.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ],
        },
    },
]


DATABASES = {
    "default": {
        "NAME": "ydb_db",
        "ENGINE": "ydb_backend.backend",
        "HOST": "localhost",
        "PORT": "2136",
        "DATABASE": "/local",
        "OPTIONS": {
            "credentials": None,
        },
    }
}
