"""Settings do projeto sandbox rodando Django 6.1.

Usa o mesmo ``sandbox_app`` (pasta ``sandbox/sandbox_app``) que o projeto
irmão ``sandbox/django52``, para testar o plugin nas duas versões do Django
sem duplicar app/models/migrations — só o venv (e a versão do Django nele
instalada) difere entre os dois.

Rode com:

    cd sandbox/django61
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver 0.0.0.0:8061
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # sandbox/django61/
SANDBOX_ROOT = BASE_DIR.parent  # sandbox/
sys.path.insert(0, str(SANDBOX_ROOT))

SECRET_KEY = "sandbox-django61-not-for-production"  # noqa: S105
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_results",
    "django_celery_task_monitor",
    "sandbox_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Celery -------------------------------------------------------------
# "memory://" não exige Redis/RabbitMQ instalado. CELERY_TASK_STORE_EAGER_RESULT
# é essencial: sem ela, tarefas eager não persistem o TaskResult e o polling
# do django_celery_task_monitor nunca sairia de PENDING.
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_TASK_STORE_EAGER_RESULT = True

# --- django_celery_task_monitor ------------------------------------------
CELERY_TASK_MONITOR_POLL_INTERVAL = 3000
