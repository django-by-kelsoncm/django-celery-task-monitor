============
JavaScript
============

``task-poll.js`` é auto-contido (sem dependências externas, sem jQuery) e
mora em ``django_celery_task_monitor/static/django_celery_task_monitor/js/task-poll.js``.

Auto-inicialização
=====================

Assim que o script carrega, ele varre a página por elementos com o atributo
``data-poll-url`` (exatamente o que ``task_status_badge.html`` **e**
``task_status_panel.html`` renderizam) e começa a sondar cada um
automaticamente. Isso é o que faz a coluna do changelist e o painel do
change form "simplesmente funcionarem" quando você usa
``CeleryTaskMonitorMixin`` — nenhum ``<script>`` de inicialização manual é
necessário.

Badge vs. painel
===================

O mesmo ``task-poll.js`` atualiza os dois tipos de elemento, diferenciados
pela estrutura interna:

- **Badge** (``task_status_badge.html``): tem um ``.task-status-badge__label``
  — recebe só o rótulo curto (``status_display``, ex.: "Concluída").
- **Painel** (``task_status_panel.html``): tem um ``.task-status-panel__message``
  — recebe a frase completa, recomposta a cada poll **e** a cada segundo no
  cliente (para o relógio de "há X tempo" andar sem esperar o próximo poll).
  Fora isso, ambos compartilham a mesma lógica de dedupe, cleanup e troca de
  classe CSS por status.

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
   * - ``messages``
     - Sobrescreve os textos padrão (pt-BR) usados nos painéis para esta chamada — ver abaixo.

``TaskPoll.stop(el)``
------------------------

Para o polling de um elemento específico e limpa o ``setInterval``
correspondente.

``TaskPoll.stopAll()``
--------------------------

Para o polling de todos os elementos atualmente monitorados.

``TaskPoll.configure(options)``
-----------------------------------

Sobrescreve os textos padrão globalmente, para todas as chamadas de
``init()`` feitas depois (incluindo a auto-inicialização):

.. code-block:: html

   <script src="{% static 'django_celery_task_monitor/js/task-poll.js' %}"></script>
   <script>
     TaskPoll.configure({
       messages: {
         queued: "Waiting to start.",
         running: "Running for {time}.",
         progress: "{percent}% complete.",
         success: "Finished successfully.",
         failure: "Finished with an error.",
         revoked: "Cancelled.",
         none: "No task in progress.",
       },
     });
   </script>

Chame ``TaskPoll.configure()`` **antes** do ``DOMContentLoaded`` disparar
(ex.: logo depois do ``<script src="task-poll.js">``, no ``<head>``) para
que a auto-inicialização já use os textos customizados. As chaves
disponíveis são exatamente as do exemplo acima; ``{time}`` e ``{percent}``
são substituídos literalmente (não são expressões).

Note que isso só afeta o texto renderizado **no cliente** — o texto usado
no primeiro render do servidor (antes do JavaScript rodar) e no campo
``message`` do payload JSON vêm de ``models.py`` e usam o mecanismo normal
de i18n do Django (``gettext``), independentemente disso. Veja
:doc:`advanced` para como as duas fontes se relacionam.

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
     "status": "PROGRESS",
     "status_display": "Em processamento",
     "message": "Tarefa em processamento há 12s. Processamento em 50%.",
     "is_finished": false,
     "created_at": "2026-08-21T12:47:30.779935+00:00",
     "updated_at": "2026-08-21T12:47:35.299003+00:00",
     "started_at": "2026-08-21T12:47:31.100000+00:00",
     "progress": {"percent": 50}
   }

- ``message``: frase pronta (mesmo texto que o painel mostra), útil para
  qualquer consumidor do endpoint que não use ``task-poll.js``.
- ``started_at``: quando a execução realmente começou, segundo
  ``TaskResult.date_started`` — ``null`` se o Celery ainda não registrou
  isso (requer ``CELERY_TASK_TRACK_STARTED = True`` no projeto host, ver
  :doc:`configuration`). ``task-poll.js`` usa este campo para calcular o
  tempo decorrido no relógio local.
- ``progress``: o ``dict`` decodificado de um estado customizado (ex.
  ``PROGRESS``), ou ``null`` para estados padrão do Celery — ver
  :doc:`advanced`.

Quando ``status`` é ``FAILURE``, um campo ``error`` adicional aparece, com
``{"message": ..., "traceback": ...}`` — ``traceback`` só vem preenchido
para quem tem a permissão ``view_task_trace`` (ver :doc:`permissions`).
