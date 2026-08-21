"""App Celery do sandbox em Django 5.2."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("sandbox_django52")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["sandbox_app"])
