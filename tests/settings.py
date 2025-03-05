from pathlib import Path
BASE_DIR = Path(__file__).parent

DATABASES = {
    "default": {
        'ENGINE': 'ydb_backend.backend',
        'ENDPOINT': 'grpc://localhost:2136',
        'DATABASE': '/local',
        'OPTIONS': {
            'credentials': None,
        },
    },
    "other": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}
