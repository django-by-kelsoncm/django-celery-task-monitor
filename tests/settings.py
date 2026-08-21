"""Settings mínimas do Django usadas pela suíte de testes (pytest-django).

Reaproveita a app ``example_app`` (pasta ``example/``) como modelo alvo do
``GenericForeignKey`` de ``TaskLog``, evitando duplicar um modelo de teste.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "example"))

SECRET_KEY = "test-secret-key"  # noqa: S105
DEBUG = False
USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "pt-br"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django_celery_results",
    "django_celery_task_monitor",
    "example_app",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ROOT_URLCONF = "tests.urls"
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_RESULT_BACKEND = "django-db"

CELERY_TASK_MONITOR_POLL_INTERVAL = 4000
