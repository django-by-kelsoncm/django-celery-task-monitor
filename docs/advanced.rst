==============
Uso Avançado
==============

Disparando tarefas em outros lugares (actions, etc.)
========================================================

``start_task()``/``create_task_log()`` não são exclusivos de
``response_change`` — funcionam em qualquer lugar do ``ModelAdmin``,
inclusive numa ``action`` de changelist (uma tarefa por objeto
selecionado):

.. code-block:: python

   class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
       actions = ["processar_selecionados_async"]

       @admin.action(description="Processar selecionados (assíncrono)")
       def processar_selecionados_async(self, request, queryset):
           for obj in queryset:
               self.start_task(request, obj, minha_task, obj.id)
           self.message_user(request, f"{queryset.count()} tarefa(s) iniciada(s)!")

Se a tarefa já foi disparada de outro jeito (``apply_async()`` com opções
customizadas, por exemplo) e você só tem o ``task_id`` em mãos, use
``create_task_log()`` diretamente — é o que ``start_task()`` usa por baixo:

.. code-block:: python

   result = minha_task.apply_async((obj.id,), countdown=60)
   self.create_task_log(request, obj, result.id, task_name="minha_task")

``task_name`` é opcional em ``start_task()`` — é derivado automaticamente de
``task.name`` (todo ``@shared_task``/``@app.task`` tem esse atributo); passe
``task_name=`` explicitamente só para sobrescrever.

Intervalo de polling por ``ModelAdmin``
==========================================

.. code-block:: python

   class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
       celery_poll_interval = 3000  # 3s, em vez do default global

Quando omitido (``None``, o default), o intervalo efetivo vem de
``CELERY_TASK_MONITOR_POLL_INTERVAL`` (ver :doc:`configuration`).
``get_celery_poll_interval()`` calcula esse valor e pode ser sobrescrito se a
lógica precisar ser dinâmica (por exemplo, por usuário ou por objeto).

Nome customizado da coluna
=============================

Use ``celery_task_field`` quando ``task_status_column`` colidir com outro
atributo já existente na sua ``ModelAdmin``:

.. code-block:: python

   class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
       celery_task_field = "status_da_tarefa"
       list_display = ["nome", "status_da_tarefa"]

Internamente, o mixin cria uma cópia do método de renderização com o nome
indicado, evitando que você precise reimplementar a lógica de busca do
``TaskLog``.

Customizando o template do badge
====================================

``task_status_badge.html`` é resolvido pelo mecanismo normal de templates do
Django — para customizá-lo, crie um arquivo com o mesmo caminho relativo em
um diretório de templates do seu projeto que tenha prioridade sobre o do
plugin:

.. code-block:: text

   seu_projeto/templates/django_celery_task_monitor/task_status_badge.html

O contexto disponível inclui ``task_log``, ``status``, ``status_display``,
``poll_url`` e ``poll_interval``. Mantenha o atributo ``data-poll-url`` no
elemento raiz — é ele que ``task-poll.js`` usa para descobrir o que sondar.

Customizando o painel de status do change form
===================================================

``task_status_panel.html`` (diferente de ``task_status_badge.html``, que é
um rótulo curto) mostra a frase completa de status. Sobrescreva do mesmo
jeito:

.. code-block:: text

   seu_projeto/templates/django_celery_task_monitor/task_status_panel.html

O contexto inclui ``task_log``, ``status``, ``message`` (a frase já
composta pelo Python, usada no primeiro render antes do JavaScript
assumir), ``poll_url`` e ``poll_interval``. Assim como o badge, mantenha
``data-poll-url`` no elemento raiz. O elemento com a classe
``task-status-panel__message`` é o que ``task-poll.js`` atualiza a cada
poll (e a cada segundo, localmente, para o relógio de tempo decorrido —
ver :doc:`javascript`).

Endpoint REST fora do admin
==============================

``CeleryTaskMonitorMixin`` já cria uma rota por ``ModelAdmin``. Se preferir
um único endpoint compartilhado fora do admin, use a view genérica:

.. code-block:: python

   # urls.py
   from django_celery_task_monitor.views import TaskStatusView

   urlpatterns = [
       path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
   ]

Diferente da rota do mixin (que checa ``has_view_permission`` do
``ModelAdmin``), ``TaskStatusView`` só exige que o usuário esteja
autenticado (``LoginRequiredMixin``) — ajuste a permissão sobrescrevendo
``get()`` se precisar de uma checagem mais estrita.

Usando o badge fora do admin
================================

.. code-block:: html+django

   {% load task_monitor_tags %}

   {% task_status_badge my_task_log %}

   {# com URL/intervalo de polling customizados: #}
   {% task_status_badge my_task_log poll_url=my_poll_url poll_interval=3000 %}

   {# inclui o <script> do plugin com a inicialização já feita: #}
   {% task_poll_script ".task-status-badge" %}

Veja a lista completa de tags em :doc:`api-reference`.

Progresso percentual
========================

Dentro de uma tarefa com ``bind=True``:

.. code-block:: python

   @shared_task(bind=True)
   def minha_task(self, ...):
       for step, total in enumerate(passos, start=1):
           ...
           self.update_state(state="PROGRESS", meta={"percent": round(step / total * 100)})

``TaskLog.get_progress()`` decodifica esse ``meta`` (guardado pelo Celery no
campo ``result`` do ``TaskResult`` — não há campo próprio de "progresso" no
Celery, então é assim que qualquer estado customizado transporta dados). O
payload JSON do polling inclui ``progress`` (o dict decodificado, ou
``None``) e ``message`` já pronta com "Processamento em X%." anexado quando
``progress.percent`` existe. Isso funciona para o nome de estado
``"PROGRESS"`` ou qualquer outro nome customizado — o único requisito é que
o ``result`` codificado seja um JSON decodificável para um ``dict`` (o
padrão do Celery, ``content_type == "application/json"``).

Mensagens customizadas ("Tarefa enfileirada.", etc.)
========================================================

Os textos padrão (pt-BR) usados no painel vêm de duas fontes:

- No servidor (primeiro render, antes do JS assumir, e no campo ``message``
  do payload JSON): ``django_celery_task_monitor.models._compose_status_message``,
  usando ``gettext`` — traduzível via o mecanismo normal de i18n do Django
  (ver ``CONTRIBUTING.md`` para regenerar/compilar traduções).
- No cliente (recalculado a cada segundo, para o relógio de "há X tempo"
  andar sem round-trip ao servidor): ``DEFAULT_MESSAGES`` em
  ``task-poll.js``, sobrescrevível por chamada via
  ``TaskPoll.init(selector, {messages: {...}})`` ou globalmente via
  ``TaskPoll.configure({messages: {...}})``. Ver :doc:`javascript` para a
  lista completa de chaves.

As duas fontes usam o mesmo texto pt-BR por padrão, mas são independentes —
customizar uma não afeta a outra.
