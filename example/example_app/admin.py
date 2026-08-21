"""ModelAdmin de exemplo demonstrando o uso de ``CeleryTaskMonitorMixin``."""

from django.contrib import admin
from django.http import HttpResponseRedirect

from django_celery_task_monitor.admin import CeleryTaskMonitorMixin

from .models import Relatorio
from .tasks import processar_relatorio


@admin.register(Relatorio)
class RelatorioAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
    list_display = ["nome", "processado", "task_status_column"]

    # Opcional: sobrescreve o intervalo global de polling (ms) só para esta ModelAdmin.
    celery_poll_interval = 3000
    actions = ["processar_selecionados_async"]

    def response_change(self, request, obj):
        if "_processar-async" in request.POST:
            # start_task() dispara processar_relatorio.delay(obj.id) e já
            # registra o TaskLog correspondente (content_type/object_id/
            # task_id/started_by), sem precisar montar isso na mão.
            self.start_task(request, obj, processar_relatorio, obj.id)
            self.message_user(request, "Task iniciada!")
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @admin.action(description="Processar selecionados (assíncrono)")
    def processar_selecionados_async(self, request, queryset):
        """Dispara uma tarefa por relatório selecionado no changelist.

        Mesmo ``start_task()`` do ``response_change`` acima — funciona
        idêntico numa ``action`` de changelist, uma chamada por objeto do
        queryset.
        """
        for relatorio in queryset:
            self.start_task(request, relatorio, processar_relatorio, relatorio.id)
        self.message_user(request, f"{queryset.count()} tarefa(s) iniciada(s)!")
