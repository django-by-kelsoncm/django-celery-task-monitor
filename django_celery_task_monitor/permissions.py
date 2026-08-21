"""Utilitários de controle de permissão para o monitoramento de tarefas.

A permissão ``view_task_trace`` (registrada em :class:`TaskLog.Meta.permissions
<django_celery_task_monitor.models.TaskLog>`) controla quem pode ver o
stacktrace completo de uma tarefa que falhou. Usuários sem essa permissão
recebem apenas uma mensagem amigável, conforme
:data:`django_celery_task_monitor.settings.FRIENDLY_ERROR_MESSAGE`.
"""

from __future__ import annotations

from typing import Any

from . import settings as app_settings


def user_can_view_task_trace(user: Any) -> bool:
    """Retorna ``True`` se ``user`` pode ver o stacktrace completo de uma tarefa.

    Superusuários sempre podem. Usuários anônimos (ou ``None``) nunca podem.
    Demais usuários precisam da permissão configurada em
    :data:`django_celery_task_monitor.settings.TASK_TRACE_PERMISSION`.

    ``user`` aceita tanto um ``AbstractBaseUser`` autenticado quanto um
    ``AnonymousUser``/``None``, por isso o tipo é deliberadamente duck-typed
    (``has_perm`` existe em ambos, mas com bases distintas no Django).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    has_perm = getattr(user, "has_perm", None)
    return bool(has_perm(app_settings.TASK_TRACE_PERMISSION)) if has_perm else False
