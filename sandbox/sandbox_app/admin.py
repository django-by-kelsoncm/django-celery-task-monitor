"""ModelAdmin de sandbox demonstrando o uso de ``CeleryTaskMonitorMixin``."""

from django.contrib import admin
from django.http import HttpResponseRedirect

from django_celery_task_monitor.admin import CeleryTaskMonitorMixin

from .models import SandboxItem
from .tasks import processar_item


@admin.register(SandboxItem)
class SandboxItemAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
    list_display = ["nome", "processado", "task_status_column"]
    celery_poll_interval = 3000
    actions = ["processar_selecionados_async"]

    def response_change(self, request, obj):
        if "_processar-async" in request.POST:
            # start_task() dispara processar_item.delay(obj.id) e já
            # registra o TaskLog correspondente (content_type/object_id/
            # task_id/started_by), sem precisar montar isso na mão.
            self.start_task(request, obj, processar_item, obj.id)
            self.message_user(request, "Task iniciada!")
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @admin.action(description="Processar selecionados (assíncrono)")
    def processar_selecionados_async(self, request, queryset):
        """Dispara uma tarefa por item selecionado no changelist.

        Mesmo ``start_task()`` do ``response_change`` acima — funciona
        idêntico numa ``action`` de changelist, uma chamada por objeto do
        queryset.
        """
        for item in queryset:
            self.start_task(request, item, processar_item, item.id)
        self.message_user(request, f"{queryset.count()} tarefa(s) iniciada(s)!")
