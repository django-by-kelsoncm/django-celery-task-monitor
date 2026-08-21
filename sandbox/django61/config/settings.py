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
# Broker "filesystem://": fila real baseada em arquivos em disco, sem exigir
# Redis/RabbitMQ instalado. Ao contrário de CELERY_TASK_ALWAYS_EAGER (que
# roda a task de forma síncrona, bloqueando a própria requisição que a
# disparou), isso permite testar o ciclo completo de verdade — um worker
# separado processa a fila em background, então o polling do plugin chega a
# ver os estados intermediários (enfileirada → em processamento → %  →
# concluída). Rode o worker em outro terminal:
#
#   cd sandbox/django61 && source .venv/bin/activate
#   celery -A config worker --loglevel=info --pool=solo
#
# (--pool=solo evita a complexidade de multiprocessing, ideal para sandbox
# local de um único worker.)
#
# data_folder_in/data_folder_out precisam apontar para o MESMO diretório
# aqui: o transporte filesystem do Kombu é assimétrico por design (quem
# publica escreve em data_folder_out, quem consome lê de data_folder_in —
# pensado para produtor/consumidor com configs "trocadas" entre si), mas
# como o processo web (produtor) e o `celery worker` (consumidor) leem
# esse MESMO settings.py, só funciona se as duas chaves coincidirem.
_BROKER_DIR = BASE_DIR / "broker_queue"
(_BROKER_DIR / "queue").mkdir(parents=True, exist_ok=True)
(_BROKER_DIR / "processed").mkdir(parents=True, exist_ok=True)
(_BROKER_DIR / "control").mkdir(parents=True, exist_ok=True)

CELERY_BROKER_URL = "filesystem://"
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "data_folder_in": str(_BROKER_DIR / "queue"),
    "data_folder_out": str(_BROKER_DIR / "queue"),
    "data_folder_processed": str(_BROKER_DIR / "processed"),
    "control_folder": str(_BROKER_DIR / "control"),
}
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
# Sem isso, o Celery nunca registra STARTED/date_started, e o painel ao
# vivo do plugin ficaria preso em "Tarefa enfileirada." mesmo com a tarefa
# já em execução.
CELERY_TASK_TRACK_STARTED = True

# --- django_celery_task_monitor ------------------------------------------
CELERY_TASK_MONITOR_POLL_INTERVAL = 3000
