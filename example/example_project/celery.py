"""App Celery do projeto de exemplo.

Em produção, aponte ``CELERY_BROKER_URL``/``CELERY_RESULT_BACKEND`` para
Redis/RabbitMQ. Este exemplo usa ``django-celery-results`` como backend de
resultados, que é a peça que o ``django_celery_task_monitor`` consulta.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

app = Celery("example_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
