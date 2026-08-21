"""Tarefa Celery de exemplo usada para demonstrar o django_celery_task_monitor.

``bind=True`` dá acesso a ``self.update_state()``, usado aqui para publicar
progresso percentual (lido por ``TaskLog.get_progress()``/o painel ao vivo
do change form). Em modo eager (``CELERY_TASK_ALWAYS_EAGER = True``, o
padrão deste exemplo) a tarefa roda de forma síncrona dentro da própria
requisição HTTP que a disparou, então o navegador só chega a fazer polling
DEPOIS que ela já terminou — os estados intermediários ("em processamento",
"42%") não ficam visíveis, mesmo estando corretamente implementados aqui.
Para ver a progressão completa ao vivo, use um broker de verdade (Redis) e
um worker Celery rodando à parte.
"""

import time

from celery import shared_task


@shared_task(name="example_app.processar_relatorio", bind=True)
def processar_relatorio(self, relatorio_id: int) -> str:
    """Simula um processamento demorado, publicando progresso, e marca o relatório."""
    from .models import Relatorio

    total_steps = 4
    for step in range(1, total_steps + 1):
        time.sleep(0.5)
        self.update_state(state="PROGRESS", meta={"percent": round(step / total_steps * 100)})

    relatorio = Relatorio.objects.get(pk=relatorio_id)
    relatorio.processado = True
    relatorio.save(update_fields=["processado"])
    return f"Relatório {relatorio_id} processado com sucesso."
