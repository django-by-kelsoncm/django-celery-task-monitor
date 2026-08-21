"""ModelAdmin de sandbox demonstrando o uso de ``CeleryTaskMonitorMixin``."""

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect

from django_celery_task_monitor.admin import CeleryTaskMonitorMixin
from django_celery_task_monitor.models import TaskLog

from .models import SandboxItem
from .tasks import processar_item


@admin.register(SandboxItem)
class SandboxItemAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
    list_display = ["nome", "processado", "task_status_column"]
    celery_poll_interval = 3000

    def response_change(self, request, obj):
        if "_processar-async" in request.POST:
            task = processar_item.delay(obj.id)

            TaskLog.objects.create(
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.id,
                task_id=task.id,
                task_name="sandbox_app.processar_item",
                started_by=request.user,
            )

            self.message_user(request, "Task iniciada!")
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)
