"""Configuração da aplicação Django ``django_celery_task_monitor``."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CeleryTaskMonitorConfig(AppConfig):
    """Configuração padrão da app de monitoramento de tarefas Celery."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_celery_task_monitor"
    label = "django_celery_task_monitor"
    verbose_name = _("Monitoramento de Tarefas Celery")
