from pathlib import Path
BASE_DIR = Path(__file__).parent


DATABASES = {
    "default": {
        'ENGINE': 'ydb_backend.backend',
        'HOST': 'localhost',
        'PORT': '2136',
        'DATABASE': '/local',
        'OPTIONS': {
            'credentials': None,
        },
    }
}

SECRET_KEY = "django_tests_secret_key"