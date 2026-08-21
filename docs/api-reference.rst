====================
Referência da API
====================

``django_celery_task_monitor.models``
========================================

.. autoclass:: django_celery_task_monitor.models.TaskLog
   :members:
   :undoc-members:

Estados possíveis (``TaskLog.status``): ``PENDING``, ``STARTED``, ``RETRY``,
``SUCCESS``, ``FAILURE``, ``REVOKED`` — os mesmos nomes usados pelo Celery
(``celery.states``), espelhados localmente para que este módulo não precise
importar o pacote ``celery`` diretamente.

``django_celery_task_monitor.admin``
=======================================

.. autoclass:: django_celery_task_monitor.admin.CeleryTaskMonitorMixin
   :members:
   :undoc-members:

.. autoclass:: django_celery_task_monitor.admin.TaskLogAdmin
   :members:
   :undoc-members:

``django_celery_task_monitor.views``
=======================================

.. autoclass:: django_celery_task_monitor.views.TaskStatusView
   :members:
   :undoc-members:

``django_celery_task_monitor.permissions``
=============================================

.. autofunction:: django_celery_task_monitor.permissions.user_can_view_task_trace

``django_celery_task_monitor.settings``
==========================================

Ver :doc:`configuration` para a lista completa de settings lidas deste
módulo.

Template tags (``{% load task_monitor_tags %}``)
=====================================================

.. list-table::
   :header-rows: 1

   * - Tag
     - Descrição
   * - ``{% task_status_badge task_log %}``
     - Renderiza o badge de status de um ``TaskLog``.
   * - ``{% task_poll_script selector %}``
     - Emite o ``<script>`` do plugin já com a inicialização do polling para ``selector``.
   * - ``{% task_monitor_static_url %}``
     - URL estática de ``task-poll.js``.
   * - ``{% task_monitor_static_css_url %}``
     - URL estática do CSS opcional do badge.

Templates
===========

.. list-table::
   :header-rows: 1

   * - Template
     - Uso
   * - ``django_celery_task_monitor/task_status_badge.html``
     - Badge de status usado no changelist, no ``TaskLogAdmin`` e na tag ``task_status_badge``.
   * - ``django_celery_task_monitor/task_log_detail.html``
     - Bloco de detalhe de um ``TaskLog`` (status, metadados, erro), para uso livre em templates do projeto host.
