"""Tarefa Celery de exemplo usada para exercitar o django_celery_task_monitor.

``bind=True`` dá acesso a ``self.update_state()``, usado aqui para publicar
progresso percentual (lido por ``TaskLog.get_progress()``/o painel ao vivo
do change form). O sandbox roda com um broker real (``filesystem://``, ver
``config/settings.py``) e precisa de um worker Celery rodando à parte para
processar a fila — sem isso, a task fica só enfileirada e nunca executa
(veja ``sandbox/README.md``). ``STEP_SECONDS`` é deliberadamente alto (mais
que o ``celery_poll_interval`` da ``ModelAdmin``) para dar tempo de ver o
painel evoluir por pelo menos 2-3 polls antes de terminar.
"""

import time

from celery import shared_task

STEP_SECONDS = 2
TOTAL_STEPS = 5


@shared_task(name="sandbox_app.processar_item", bind=True)
def processar_item(self, item_id: int) -> str:
    """Simula um processamento demorado (~10s), publicando progresso, e marca o item."""
    from .models import SandboxItem

    for step in range(1, TOTAL_STEPS + 1):
        time.sleep(STEP_SECONDS)
        self.update_state(state="PROGRESS", meta={"percent": round(step / TOTAL_STEPS * 100)})

    item = SandboxItem.objects.get(pk=item_id)
    item.processado = True
    item.save(update_fields=["processado"])
    return f"Item {item_id} processado com sucesso."
