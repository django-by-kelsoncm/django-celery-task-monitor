"""Tarefa Celery de exemplo usada para demonstrar o django_celery_task_monitor."""

import time

from celery import shared_task


@shared_task(name="example_app.processar_relatorio")
def processar_relatorio(relatorio_id: int) -> str:
    """Simula um processamento demorado e marca o relatório como processado."""
    from .models import Relatorio

    time.sleep(2)
    relatorio = Relatorio.objects.get(pk=relatorio_id)
    relatorio.processado = True
    relatorio.save(update_fields=["processado"])
    return f"Relatório {relatorio_id} processado com sucesso."
