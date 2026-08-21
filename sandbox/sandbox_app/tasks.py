"""Tarefa Celery de exemplo usada para exercitar o django_celery_task_monitor."""

import time

from celery import shared_task


@shared_task(name="sandbox_app.processar_item")
def processar_item(item_id: int) -> str:
    """Simula um processamento demorado e marca o item como processado."""
    from .models import SandboxItem

    time.sleep(2)
    item = SandboxItem.objects.get(pk=item_id)
    item.processado = True
    item.save(update_fields=["processado"])
    return f"Item {item_id} processado com sucesso."
