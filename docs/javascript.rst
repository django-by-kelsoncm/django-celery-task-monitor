============
JavaScript
============

``task-poll.js`` é auto-contido (sem dependências externas, sem jQuery) e
mora em ``django_celery_task_monitor/static/django_celery_task_monitor/js/task-poll.js``.

Auto-inicialização
=====================

Assim que o script carrega, ele varre a página por elementos com o atributo
``data-poll-url`` (exatamente o que ``task_status_badge.html`` renderiza) e
começa a sondar cada um automaticamente. Isso é o que faz a coluna do
changelist "simplesmente funcionar" quando você usa
``CeleryTaskMonitorMixin`` — nenhum ``<script>`` de inicialização manual é
necessário.

API pública (``window.TaskPoll``)
=====================================

``TaskPoll.init(selector, options)``
---------------------------------------

Inicia o polling de todos os elementos que casam com ``selector``.

.. code-block:: html

   <script src="{% static 'django_celery_task_monitor/js/task-poll.js' %}"></script>
   <script>
     TaskPoll.init(".task-badge", {
       pollInterval: 5000,
       endpoint: "/admin/task-status/",  // opcional se o elemento já tem data-poll-url
       onUpdate: function (data, el) { /* a cada resposta recebida */ },
       onSuccess: function (data, el) { console.log("Task concluída!", data); },
       onError: function (data, el) { console.warn("Task falhou", data); },
     });
   </script>

Opções:

.. list-table::
   :header-rows: 1

   * - Opção
     - Descrição
   * - ``endpoint``
     - URL de polling comum a todos os elementos (ignorada se o elemento já tiver ``data-poll-url``).
   * - ``pollInterval``
     - Intervalo em ms (default: 5000). ``data-poll-interval`` no elemento tem prioridade.
   * - ``onUpdate(data, el)``
     - Chamado a cada resposta recebida do endpoint.
   * - ``onSuccess(data, el)``
     - Chamado quando a tarefa termina com ``status === "SUCCESS"``.
   * - ``onError(data, el)``
     - Chamado quando a tarefa falha, é revogada, ou o ``fetch`` dá erro.

``TaskPoll.stop(el)``
------------------------

Para o polling de um elemento específico e limpa o ``setInterval``
correspondente.

``TaskPoll.stopAll()``
--------------------------

Para o polling de todos os elementos atualmente monitorados.

Prevenção de duplicação e memory leaks
==========================================

- Cada elemento monitorado recebe o atributo ``data-task-poll-active``, que
  serve como guarda contra polling duplicado mesmo que o script seja
  avaliado mais de uma vez na mesma página (por exemplo, HTML re-inserido
  via AJAX).
- Um ``MutationObserver`` observa remoções no DOM e limpa automaticamente o
  ``setInterval`` de qualquer badge removido da página, evitando memory
  leaks em SPAs ou changelists recarregados dinamicamente.
- O polling de um elemento para sozinho assim que a tarefa atinge um estado
  final (``SUCCESS``, ``FAILURE`` ou ``REVOKED`` — ver ``data.is_finished``
  no payload JSON).

Formato do payload JSON
===========================

Cada resposta do endpoint de polling (via mixin ou ``TaskStatusView``) tem o
formato:

.. code-block:: json

   {
     "task_id": "9c4b7a0a-...",
     "task_name": "example_app.processar_relatorio",
     "status": "SUCCESS",
     "status_display": "Concluída",
     "is_finished": true,
     "created_at": "2026-08-21T12:47:30.779935+00:00",
     "updated_at": "2026-08-21T12:47:35.299003+00:00"
   }

Quando ``status`` é ``FAILURE``, um campo ``error`` adicional aparece, com
``{"message": ..., "traceback": ...}`` — ``traceback`` só vem preenchido
para quem tem a permissão ``view_task_trace`` (ver :doc:`permissions`).
