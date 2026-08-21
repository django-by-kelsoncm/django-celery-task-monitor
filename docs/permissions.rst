=============
Permissões
=============

O plugin usa as permissões padrão do Django para o modelo ``TaskLog`` mais
uma permissão customizada:

.. list-table::
   :header-rows: 1

   * - Permissão
     - Origem
     - Controla
   * - ``django_celery_task_monitor.view_tasklog``
     - Padrão do Django (qualquer modelo ganha automaticamente)
     - Acesso ao changelist/detail do ``TaskLogAdmin``, e (via ``has_view_permission``) acesso ao endpoint REST de polling de cada ``ModelAdmin`` que usa o mixin.
   * - ``django_celery_task_monitor.change_tasklog``
     - Padrão do Django
     - Reservada para uso futuro (ex.: reprocessar tarefas diretamente do ``TaskLogAdmin``); hoje ``TaskLogAdmin`` é somente leitura (``has_add_permission`` retorna ``False``).
   * - ``django_celery_task_monitor.delete_tasklog``
     - Padrão do Django
     - Exclusão de registros de ``TaskLog`` pelo admin.
   * - ``django_celery_task_monitor.view_task_trace``
     - Customizada (``TaskLog.Meta.permissions``)
     - Ver o stacktrace completo de uma tarefa que falhou (no ``TaskLogAdmin`` e via ``TaskLog.get_error_details(user)``).

Como funciona ``view_task_trace``
=====================================

.. autofunction:: django_celery_task_monitor.permissions.user_can_view_task_trace
   :no-index:

Em resumo:

- **Superusuários** sempre veem o stacktrace completo.
- **Usuários com a permissão ``view_task_trace``** também veem.
- **Demais usuários autenticados** veem apenas a mensagem amigável
  configurada em ``CELERY_TASK_MONITOR_FRIENDLY_ERROR_MESSAGE``
  (ver :doc:`configuration`).
- **Usuários anônimos** (``None``/``AnonymousUser``) nunca veem nada além da
  mensagem amigável.

Onde isso é aplicado
========================

1. ``TaskLog.get_error_details(user)`` — usado pelo payload JSON do
   endpoint de polling (campo ``error``) e pelo ``TaskLogAdmin``.
2. ``TaskLogAdmin.get_fields()`` — remove o campo ``full_traceback`` do
   formulário inteiro para quem não tem a permissão, em vez de só ocultar
   visualmente (o HTML nunca chega a ser gerado para esse usuário).

Concedendo a permissão
=========================

Como qualquer permissão do Django, pode ser concedida via admin
(``Usuários`` → escolher usuário → ``Permissões de usuário``) ou por script:

.. code-block:: python

   from django.contrib.auth.models import Permission

   permission = Permission.objects.get(
       content_type__app_label="django_celery_task_monitor",
       codename="view_task_trace",
   )
   usuario.user_permissions.add(permission)
