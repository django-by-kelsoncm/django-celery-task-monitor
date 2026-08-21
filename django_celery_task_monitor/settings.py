"""Defaults configuráveis do plugin, lidos a partir do ``settings.py`` do projeto host.

Nenhum valor aqui é obrigatório: o projeto host pode sobrescrever qualquer
uma destas chaves diretamente no ``settings.py`` usando os nomes indicados
em cada constante (ex.: ``CELERY_TASK_MONITOR_POLL_INTERVAL``).
"""

from django.conf import settings
from django.utils.translation import gettext_lazy as _

#: Intervalo padrão (em milissegundos) usado pelo JavaScript de polling
#: quando o ``ModelAdmin`` não define ``celery_poll_interval``.
DEFAULT_POLL_INTERVAL: int = getattr(settings, "CELERY_TASK_MONITOR_POLL_INTERVAL", 5000)

#: Nome da permissão que libera a visualização do stacktrace completo.
#: Usuários sem essa permissão (e que não sejam superusuários) recebem
#: apenas uma mensagem de erro amigável.
TASK_TRACE_PERMISSION: str = getattr(
    settings,
    "CELERY_TASK_MONITOR_TRACE_PERMISSION",
    "django_celery_task_monitor.view_task_trace",
)

#: Mensagem amigável exibida a usuários sem permissão para ver o stacktrace.
FRIENDLY_ERROR_MESSAGE = getattr(
    settings,
    "CELERY_TASK_MONITOR_FRIENDLY_ERROR_MESSAGE",
    _("A tarefa falhou. Entre em contato com o administrador do sistema para mais detalhes."),
)

#: Tamanho máximo (em número de registros) retornado por padrão no changelist do admin.
DEFAULT_LIST_PER_PAGE: int = getattr(settings, "CELERY_TASK_MONITOR_LIST_PER_PAGE", 50)
