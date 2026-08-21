"""Settings do projeto Django de exemplo, demonstrando o django_celery_task_monitor.

Rode com:

    cd example
    pip install -e "..[dev]"
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

Para processar tarefas de verdade é preciso um worker Celery e um broker
(Redis por padrão). Para apenas explorar o admin, ``CELERY_TASK_ALWAYS_EAGER``
já está ativado abaixo, então as tarefas rodam de forma síncrona, sem worker.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-only-not-for-production"  # noqa: S105
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
    "example_app",
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

ROOT_URLCONF = "example_project.urls"

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

WSGI_APPLICATION = "example_project.wsgi.application"

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

# --- Celery -----------------------------------------------------------------
# "memory://" não exige Redis/RabbitMQ instalado, então o exemplo roda de
# imediato. Em produção, aponte para um broker de verdade, ex.:
#   CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_TASK_ALWAYS_EAGER = True  # facilita rodar o exemplo sem worker/broker
CELERY_TASK_EAGER_PROPAGATES = False
# Sem isso, tarefas eager não persistem o TaskResult no backend, e o polling
# do django_celery_task_monitor nunca veria o status mudar de PENDING.
CELERY_TASK_STORE_EAGER_RESULT = True
# Sem isso, o Celery nunca registra STARTED (nem TaskResult.date_started),
# então o painel ao vivo do plugin ficaria preso em "Tarefa enfileirada."
# mesmo com a tarefa já em execução. Note que, em modo eager, a tarefa roda
# de forma síncrona dentro da própria requisição que a disparou — então o
# navegador só chega a fazer polling DEPOIS que ela já terminou, e os
# estados intermediários não ficam visíveis mesmo com esta flag ativada
# (para ver a progressão completa ao vivo, use um broker de verdade e um
# worker Celery rodando à parte, sem CELERY_TASK_ALWAYS_EAGER).
CELERY_TASK_TRACK_STARTED = True

# --- django_celery_task_monitor ---------------------------------------------
CELERY_TASK_MONITOR_POLL_INTERVAL = 3000
