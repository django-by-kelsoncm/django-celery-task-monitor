"""Template tags para usar o monitoramento de tarefas em qualquer template.

Carregue com ``{% load task_monitor_tags %}``.
"""

from __future__ import annotations

from typing import Optional

from django import template
from django.templatetags.static import static
from django.utils.safestring import SafeString, mark_safe

from .. import settings as app_settings
from ..models import TaskLog

register = template.Library()


@register.inclusion_tag("django_celery_task_monitor/task_status_badge.html")
def task_status_badge(
    task_log: TaskLog, poll_url: Optional[str] = None, poll_interval: Optional[int] = None
):
    """Renderiza o badge de status de um :class:`TaskLog` em qualquer template.

    Exemplo::

        {% load task_monitor_tags %}
        {% task_status_badge my_task_log %}
    """
    return {
        "task_log": task_log,
        "status": task_log.status if task_log else None,
        "status_display": task_log.get_status_display() if task_log else None,
        "poll_url": poll_url,
        "poll_interval": poll_interval or app_settings.DEFAULT_POLL_INTERVAL,
    }


@register.simple_tag
def task_monitor_static_url() -> str:
    """Retorna a URL estática do arquivo ``task-poll.js`` do plugin."""
    return static("django_celery_task_monitor/js/task-poll.js")


@register.simple_tag
def task_monitor_static_css_url() -> str:
    """Retorna a URL estática do CSS opcional de badges do plugin."""
    return static("django_celery_task_monitor/css/task-monitor.css")


@register.simple_tag
def task_poll_script(
    selector: str = ".task-status-badge", poll_interval: Optional[int] = None
) -> SafeString:
    """Emite a tag ``<script>`` do plugin e o código de inicialização do polling.

    Exemplo::

        {% load task_monitor_tags %}
        {% task_poll_script ".minha-classe" %}
    """
    interval = poll_interval or app_settings.DEFAULT_POLL_INTERVAL
    script_url = static("django_celery_task_monitor/js/task-poll.js")
    html = (
        f'<script src="{script_url}"></script>\n'
        "<script>\n"
        "  document.addEventListener('DOMContentLoaded', function () {\n"
        f"    TaskPoll.init('{selector}', {{ pollInterval: {interval} }});\n"
        "  });\n"
        "</script>"
    )
    return mark_safe(html)
