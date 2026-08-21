"""Tarefa Celery de exemplo usada para exercitar o django_celery_task_monitor.

``bind=True`` dá acesso a ``self.update_state()``, usado aqui para publicar
progresso percentual (lido por ``TaskLog.get_progress()``/o painel ao vivo
do change form). Em modo eager (``CELERY_TASK_ALWAYS_EAGER = True``, o
padrão do sandbox) a tarefa roda de forma síncrona dentro da própria
requisição HTTP que a disparou, então o navegador só chega a fazer polling
DEPOIS que ela já terminou — ou seja, os estados intermediários
("em processamento", "42%") não são visíveis, mesmo estando corretamente
implementados aqui. Para ver a progressão completa ao vivo, use um broker de
verdade (Redis) e um worker Celery rodando à parte (veja ``sandbox/README.md``).
"""

import time

from celery import shared_task


@shared_task(name="sandbox_app.processar_item", bind=True)
def processar_item(self, item_id: int) -> str:
    """Simula um processamento demorado, publicando progresso, e marca o item."""
    from .models import SandboxItem

    total_steps = 4
    for step in range(1, total_steps + 1):
        time.sleep(0.5)
        self.update_state(state="PROGRESS", meta={"percent": round(step / total_steps * 100)})

    item = SandboxItem.objects.get(pk=item_id)
    item.processado = True
    item.save(update_fields=["processado"])
    return f"Item {item_id} processado com sucesso."
