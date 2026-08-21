"""App Celery do sandbox em Django 6.1."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("sandbox_django61")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["sandbox_app"])
