"""Endpoint REST genérico e independente de admin para polling de status.

Este módulo é **opcional**: :class:`~django_celery_task_monitor.admin.CeleryTaskMonitorMixin`
já registra sua própria rota de polling por ``ModelAdmin`` via ``get_urls()``.
Use ``TaskStatusView`` quando quiser um único endpoint compartilhado fora do
admin (ex.: para uma página customizada do projeto host).
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from .models import TaskLog


class TaskStatusView(LoginRequiredMixin, View):
    """View genérica que retorna o status (JSON) de um :class:`TaskLog` pelo ``task_id``.

    Para usar, registre a rota no ``urls.py`` do projeto host::

        from django_celery_task_monitor.views import TaskStatusView

        urlpatterns = [
            path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
        ]
    """

    raise_exception = False

    def get(self, request: HttpRequest, task_id: str) -> JsonResponse:
        """Retorna o payload de status da tarefa, ou 404 se ``task_id`` não existir."""
        task_log = get_object_or_404(TaskLog, task_id=task_id)
        return JsonResponse(task_log.as_status_payload(request.user))
