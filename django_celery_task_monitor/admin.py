"""Admin do ``TaskLog`` e o mixin ``CeleryTaskMonitorMixin`` reutilizável.

``TaskLogAdmin`` fornece uma interface central para consultar todas as
tarefas registradas pelo projeto host. ``CeleryTaskMonitorMixin`` é o que os
``ModelAdmin`` do projeto host usam para ganhar uma coluna de status com
polling automático via REST.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from django import forms
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, JsonResponse
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from . import settings as app_settings
from .models import FAILURE, TaskLog
from .permissions import user_can_view_task_trace

if TYPE_CHECKING:
    # Faz o mypy/django-stubs enxergar os atributos herdados de ModelAdmin
    # (self.model, self.admin_site, super().media, etc.) na mixin, sem que
    # ela precise herdar de ModelAdmin em tempo de execução — quem faz isso
    # é a classe concreta do projeto host (ex.: `class X(CeleryTaskMonitorMixin,
    # admin.ModelAdmin)`).
    _AdminBase = admin.ModelAdmin[Any]
else:
    _AdminBase = object


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    """Interface de administração para consultar todos os registros de tarefas.

    Somente leitura: instâncias de :class:`TaskLog` são sempre criadas
    programaticamente pelo projeto host (ver ``README.md``), então esta
    ``ModelAdmin`` desabilita a criação manual.
    """

    list_display = (
        "task_id",
        "task_name",
        "content_type",
        "object_id",
        "status_badge",
        "started_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "task_name", "content_type")
    search_fields = ("task_id", "task_name", "object_id")
    list_per_page = app_settings.DEFAULT_LIST_PER_PAGE
    date_hierarchy = "created_at"
    readonly_fields = (
        "content_type",
        "object_id",
        "task_id",
        "task_name",
        "status",
        "started_by",
        "created_at",
        "updated_at",
        "friendly_message",
        "full_traceback",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """``TaskLog`` é sempre criado ao disparar a tarefa, nunca manualmente."""
        return False

    def get_fields(self, request: HttpRequest, obj: Optional[TaskLog] = None):
        """Remove ``full_traceback`` dos campos exibidos a quem não tem permissão."""
        fields = list(super().get_fields(request, obj))
        if "full_traceback" in fields and not user_can_view_task_trace(request.user):
            fields.remove("full_traceback")
        return fields

    @admin.display(description=_("status"), ordering="status")
    def status_badge(self, obj: TaskLog) -> str:
        """Renderiza o badge de status reutilizando o template do plugin."""
        return render_to_string(
            "django_celery_task_monitor/task_status_badge.html",
            {"task_log": obj, "status": obj.status, "status_display": obj.get_status_display()},
        )

    @admin.display(description=_("mensagem"))
    def friendly_message(self, obj: TaskLog) -> str:
        """Mensagem de erro amigável, visível a qualquer usuário com acesso à tarefa."""
        if obj.pk is None or obj.status != FAILURE:
            return "—"
        return obj.get_error_details(None)["message"]

    @admin.display(description=_("stacktrace completo"))
    def full_traceback(self, obj: TaskLog) -> str:
        """Stacktrace completo.

        Este campo já é removido em :meth:`get_fields` para usuários sem a
        permissão ``view_task_trace``, então, quando chamado, o acesso já foi
        validado — não é necessário reverificar a permissão aqui.
        """
        if obj.pk is None or obj.status != FAILURE:
            return "—"
        return obj.get_traceback() or "—"


class CeleryTaskMonitorMixin(_AdminBase):
    """Mixin que adiciona uma coluna de status de tarefa Celery a um ``ModelAdmin``.

    Uso mínimo::

        @admin.register(MeuModelo)
        class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
            list_display = ["nome", "task_status_column"]

    Atributos configuráveis na subclasse:

    - ``celery_poll_interval``: intervalo de polling em milissegundos,
      sobrescrevendo o default global ``CELERY_TASK_MONITOR_POLL_INTERVAL``.
    - ``celery_task_field``: nome do atributo/coluna usado no ``list_display``
      (default: ``"task_status_column"``). Útil quando o nome padrão colide
      com outro atributo já existente na ``ModelAdmin``.
    """

    celery_poll_interval: Optional[int] = None
    celery_task_field: str = "task_status_column"

    @property
    def media(self) -> forms.Media:
        """Garante que ``task-poll.js`` seja carregado no changelist/changeform.

        ``task-poll.js`` se auto-inicializa em qualquer elemento com
        ``data-poll-url`` (ver o próprio arquivo), então nenhum código extra é
        necessário para o badge começar a fazer polling assim que a página carrega.
        """
        extra_media = forms.Media(
            css={"all": ("django_celery_task_monitor/css/task-monitor.css",)},
            js=("django_celery_task_monitor/js/task-poll.js",),
        )
        return super().media + extra_media

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.celery_task_field != "task_status_column":
            renderer = self._make_task_status_renderer()
            setattr(self, self.celery_task_field, renderer)

    def _make_task_status_renderer(self):
        """Cria uma cópia do renderizador de status com o nome customizado pelo usuário."""

        def _render(obj):
            return self._render_task_status(obj)

        _render.short_description = _("Status da Tarefa")  # type: ignore[attr-defined]
        return _render

    @admin.display(description=_("Status da Tarefa"))
    def task_status_column(self, obj):
        """Coluna padrão de status. Adicione ``"task_status_column"`` ao ``list_display``."""
        return self._render_task_status(obj)

    def get_celery_poll_interval(self) -> int:
        """Retorna o intervalo de polling (ms) efetivo desta ``ModelAdmin``."""
        return self.celery_poll_interval or app_settings.DEFAULT_POLL_INTERVAL

    def _latest_task_log(self, obj) -> Optional[TaskLog]:
        """Busca o :class:`TaskLog` mais recente vinculado a ``obj``."""
        content_type = ContentType.objects.get_for_model(type(obj))
        return (
            TaskLog.objects.filter(content_type=content_type, object_id=str(obj.pk))
            .order_by("-created_at")
            .first()
        )

    def _render_task_status(self, obj) -> str:
        task_log = self._latest_task_log(obj)
        if task_log is None:
            return "—"
        return render_to_string(
            "django_celery_task_monitor/task_status_badge.html",
            {
                "task_log": task_log,
                "status": task_log.status,
                "status_display": task_log.get_status_display(),
                "poll_url": self._get_task_status_url(task_log.task_id),
                "poll_interval": self.get_celery_poll_interval(),
            },
        )

    def _render_task_status_panel(self, obj) -> str:
        task_log = self._latest_task_log(obj)
        if task_log is None:
            return ""
        # get_status_message() atualiza (e persiste) task_log.status como
        # efeito colateral — precisa rodar antes de ler `.status` abaixo,
        # senão a classe CSS do painel fica presa no valor cacheado antigo
        # enquanto a mensagem já mostra o estado novo.
        message = task_log.get_status_message()
        return render_to_string(
            "django_celery_task_monitor/task_status_panel.html",
            {
                "task_log": task_log,
                "status": task_log.status,
                "message": message,
                "poll_url": self._get_task_status_url(task_log.task_id),
                "poll_interval": self.get_celery_poll_interval(),
            },
        )

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        """Injeta ``task_log_panel_html`` no contexto do change form.

        Diferente do badge do changelist (adicionado automaticamente via
        ``list_display``), o painel do change form é opt-in: o template
        ``change_form.html`` do seu ``ModelAdmin`` precisa referenciar
        ``{{ task_log_panel_html }}`` onde quiser exibi-lo (ex.: logo após o
        botão que dispara a tarefa). Isso evita que o plugin sobrescreva
        globalmente o template de todo ``ModelAdmin`` do projeto host.
        """
        if obj is not None:
            context["task_log_panel_html"] = self._render_task_status_panel(obj)
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def _url_name(self) -> str:
        opts = self.model._meta
        return f"{opts.app_label}_{opts.model_name}_celery_task_status"

    def _get_task_status_url(self, task_id: str) -> str:
        return reverse(f"admin:{self._url_name()}", args=[task_id])

    def get_urls(self):
        """Registra a rota REST de polling antes das rotas padrão do admin."""
        custom_urls = [
            path(
                "task-status/<str:task_id>/",
                self.admin_site.admin_view(self.task_status_view),
                name=self._url_name(),
            ),
        ]
        return custom_urls + super().get_urls()

    def task_status_view(self, request: HttpRequest, task_id: str) -> JsonResponse:
        """Endpoint REST de polling: retorna o status (JSON) de uma tarefa.

        Exige permissão de visualização do modelo administrado (a mesma
        permissão usada para acessar o changelist).
        """
        if not self.has_view_permission(request):
            return JsonResponse({"detail": "Permission denied."}, status=403)
        try:
            task_log = TaskLog.objects.get(task_id=task_id)
        except TaskLog.DoesNotExist:
            return JsonResponse({"detail": "Not found."}, status=404)
        return JsonResponse(task_log.as_status_payload(request.user))
