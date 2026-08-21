=====
FAQ
=====

Como mostrar uma barra de progresso, em vez de só um badge de status?
==========================================================================

Adicione um campo de progresso ao seu próprio modelo (ou a um modelo
relacionado) e atualize-o dentro da sua tarefa Celery via
``self.update_state(state="PROGRESS", meta={"percent": 42})``. Depois, ou
customize ``task_status_badge.html`` (ver :doc:`advanced`) para ler
``task_log`` e renderizar sua própria barra, ou use o callback
``onUpdate`` de ``TaskPoll.init()`` (ver :doc:`javascript`) para atualizar a
UI via JavaScript a cada resposta de polling. O plugin não impõe um formato
de barra de progresso porque isso é altamente específico de cada projeto.

Como integrar com Django-RQ (ou outra fila) em vez de Celery?
==================================================================

O plugin depende de ``django-celery-results`` porque é isso que popula
``TaskResult.status``. Para outro backend de filas, você precisaria de um
adaptador equivalente que exponha algo parecido com ``TaskResult`` (com
``task_id``, ``status``, ``result``, ``traceback``) — hoje isso está fora do
escopo do plugin. Uma alternativa mais simples: atualize ``TaskLog.status``
diretamente a partir da sua própria fila (``task_log.status = ...;
task_log.save()``), sem depender de ``update_status()``/``TaskResult``.

Como reprocessar uma tarefa que falhou?
===========================================

Isso é responsabilidade do seu ``ModelAdmin`` (o mesmo padrão de
:doc:`usage`), não do plugin — chame ``minha_task.delay(...)`` de novo e
crie um novo ``TaskLog``. O ``TaskLogAdmin`` mostra o histórico completo de
tentativas, já que cada ``TaskLog`` é imutável quanto a ``task_id``.

Os badges antigos continuam fazendo polling para sempre?
=============================================================

Não. O JavaScript para o ``setInterval`` automaticamente assim que a tarefa
atinge um status final (``SUCCESS``, ``FAILURE`` ou ``REVOKED``) — ver
:doc:`javascript`.

Por que ``object_id`` é ``CharField`` em vez de ``IntegerField``?
======================================================================

Para que ``TaskLog`` funcione com qualquer modelo, independente do tipo da
chave primária (``AutoField``, ``UUIDField``, chave primária customizada
como string, etc.) — é o mesmo padrão usado por ``GenericForeignKey`` em
outras partes do ecossistema Django.

Preciso de um worker Celery rodando para ver o plugin funcionando?
=======================================================================

Não necessariamente — veja :doc:`example-project` para rodar com
``CELERY_TASK_ALWAYS_EAGER = True``. Em produção, sim: o polling só faz
sentido quando a tarefa roda de fato em background, processada por um
worker separado do processo web.
