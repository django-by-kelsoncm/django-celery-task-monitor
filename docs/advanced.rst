==============
Uso Avançado
==============

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

Progresso além de status (barra de progresso)
=================================================

O plugin não modela progresso percentual porque isso é específico de cada
tarefa. A abordagem recomendada é usar ``self.update_state()`` dentro da sua
tarefa Celery e ler o ``meta`` correspondente no ``TaskResult`` — veja a
pergunta correspondente em :doc:`faq`.
