=====
FAQ
=====

Como mostrar uma barra de progresso, em vez de só um badge de status?
==========================================================================

O plugin já lê progresso percentual nativamente: dentro da sua tarefa
Celery (com ``bind=True``), chame ``self.update_state(state="PROGRESS",
meta={"percent": 42})``. ``TaskLog.get_progress()`` decodifica esse valor, e
tanto o payload JSON do endpoint de polling (``progress.percent``) quanto a
frase pronta do painel ao vivo (``"Processamento em 42%."``, ver
:doc:`advanced`) já refletem isso automaticamente — nenhuma customização é
necessária para o texto. Se você quiser uma barra visual (``<progress>`` ou
CSS) em vez de só o texto, use o callback ``onUpdate`` de ``TaskPoll.init()``
(ver :doc:`javascript`) para ler ``data.progress.percent`` a cada poll e
atualizar sua própria UI — isso sim é específico o bastante de cada projeto
para ficar fora do escopo do plugin.

Note que ``self.update_state()`` só é visível para quem está fazendo
polling se a tarefa realmente rodar em background (worker + broker de
verdade). Em modo eager (``CELERY_TASK_ALWAYS_EAGER = True``), a tarefa
roda de forma síncrona dentro da própria requisição que a disparou, então
os estados intermediários nunca chegam a ser vistos via polling — só o
resultado final.

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

Cliquei em disparar a tarefa e só aparece uma mensagem fixa que nunca muda
=================================================================================

Duas causas prováveis:

1. **Seu ``change_form.html`` não referencia ``{{ task_log_panel_html }}``.**
   ``CeleryTaskMonitorMixin`` injeta esse HTML pronto no contexto do change
   form (via ``render_change_form()``), mas onde ele aparece na página é
   escolha do seu template — se você só tem ``self.message_user(request,
   "Task iniciada!")`` e nenhum ``{{ task_log_panel_html }}`` no template,
   a única coisa visível será mesmo essa mensagem estática do Django, que
   nunca muda depois de renderizada. Adicione o painel (ver :doc:`usage`).
2. **``CELERY_TASK_ALWAYS_EAGER = True``.** Nesse modo a tarefa roda de
   forma síncrona dentro da própria requisição, então, quando a página
   recarrega, ela já terminou — o painel vai direto de "Tarefa enfileirada."
   para o resultado final, sem passar visivelmente por "em processamento".
   Isso é esperado (não é bug); veja a nota em :doc:`configuration`.
