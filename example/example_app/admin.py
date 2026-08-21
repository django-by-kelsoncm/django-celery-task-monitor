"""ModelAdmin de exemplo demonstrando o uso de ``CeleryTaskMonitorMixin``."""

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect

from django_celery_task_monitor.admin import CeleryTaskMonitorMixin
from django_celery_task_monitor.models import TaskLog

from .models import Relatorio
from .tasks import processar_relatorio


@admin.register(Relatorio)
class RelatorioAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
    list_display = ["nome", "processado", "task_status_column"]

    # Opcional: sobrescreve o intervalo global de polling (ms) só para esta ModelAdmin.
    celery_poll_interval = 3000

    def response_change(self, request, obj):
        if "_processar-async" in request.POST:
            task = processar_relatorio.delay(obj.id)

            TaskLog.objects.create(
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.id,
                task_id=task.id,
                task_name="example_app.processar_relatorio",
                started_by=request.user,
            )

            self.message_user(request, "Task iniciada!")
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)
