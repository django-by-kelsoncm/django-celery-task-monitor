"""Modelo ``TaskLog``: vincula tarefas Celery a qualquer instância de modelo Django.

O vínculo usa ``GenericForeignKey`` para que o plugin funcione com qualquer
modelo do projeto host, sem acoplamento a apps ou nomes específicos.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from . import settings as app_settings
from .permissions import user_can_view_task_trace

# Estados possíveis de uma tarefa Celery. Espelham ``celery.states`` para que
# este módulo não precise importar o pacote ``celery`` diretamente.
PENDING = "PENDING"
STARTED = "STARTED"
RETRY = "RETRY"
PROGRESS = "PROGRESS"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
REVOKED = "REVOKED"

STATUS_CHOICES = [
    (PENDING, _("Pendente")),
    (STARTED, _("Em execução")),
    (RETRY, _("Repetindo")),
    (PROGRESS, _("Em processamento")),
    (SUCCESS, _("Concluída")),
    (FAILURE, _("Falhou")),
    (REVOKED, _("Revogada")),
]

#: Estados finais — a tarefa não deve mais mudar de status a partir daqui.
FINISHED_STATES = frozenset({SUCCESS, FAILURE, REVOKED})

#: Estados "conhecidos" do Celery/django-celery-results. Qualquer outro valor
#: de status (como ``PROGRESS``, ou qualquer nome que a task escolha via
#: ``self.update_state(state=..., meta=...)``) é tratado como um estado
#: intermediário customizado, cujo ``result`` pode conter metadados de
#: progresso — ver :meth:`TaskLog.get_progress`.
_STANDARD_STATES = frozenset({PENDING, STARTED, RETRY, SUCCESS, FAILURE, REVOKED})


def _format_duration(total_seconds: float) -> str:
    """Formata segundos como ``"1h 2min 3s"`` (compacto, sem zero à esquerda)."""
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if hours or minutes:
        parts.append(f"{minutes}min")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _compose_status_message(
    status: str,
    started_at,
    progress: Optional[dict[str, Any]],
) -> str:
    """Monta a frase de status legível usada no painel ao vivo do change form.

    Espelhada (propositalmente com o mesmo texto) pela função ``composeMessage``
    em ``task-poll.js`` — lá ela é recalculada a cada segundo no cliente, sem
    round-trip ao servidor, para o relógio de "há X tempo" andar suavemente
    entre um poll e outro. Aqui ela só roda uma vez, no render inicial do
    painel (antes do JavaScript assumir) e no payload JSON de cada poll.
    """
    if status == SUCCESS:
        return gettext("Tarefa finalizada com sucesso.")
    if status == FAILURE:
        return gettext("Tarefa finalizada com erro.")
    if status == REVOKED:
        return gettext("Tarefa cancelada.")
    if not started_at:
        return gettext("Tarefa enfileirada.")

    elapsed = (timezone.now() - started_at).total_seconds()
    message = gettext("Tarefa em processamento há %(time)s.") % {"time": _format_duration(elapsed)}
    percent = progress.get("percent") if progress else None
    if isinstance(percent, (int, float)):
        message += " " + gettext("Processamento em %(percent)s%%.") % {"percent": percent}
    return message


class TaskLog(models.Model):
    """Registra a execução de uma tarefa Celery vinculada a um objeto qualquer.

    Instâncias são tipicamente criadas manualmente pela view/admin do projeto
    host logo após chamar ``minha_task.delay(...)``, informando o
    ``content_type``/``object_id`` do objeto relacionado e o ``task_id``
    retornado pelo Celery.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("tipo de conteúdo"),
        related_name="+",
    )
    object_id = models.CharField(_("ID do objeto"), max_length=255)
    content_object = GenericForeignKey("content_type", "object_id")

    task_id = models.CharField(_("ID da tarefa"), max_length=255, unique=True, db_index=True)
    task_name = models.CharField(_("nome da tarefa"), max_length=255, blank=True)

    status = models.CharField(
        _("status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
    )

    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="celery_task_logs",
        verbose_name=_("iniciada por"),
    )

    created_at = models.DateTimeField(_("criada em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("atualizada em"), auto_now=True)

    class Meta:
        app_label = "django_celery_task_monitor"
        verbose_name = _("registro de tarefa")
        verbose_name_plural = _("registros de tarefas")
        ordering = ["-created_at"]
        permissions = [
            ("view_task_trace", "Can view full task error trace"),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_name or self.task_id} ({self.get_status_display()})"

    def _get_task_result(self):
        """Busca o ``TaskResult`` (django-celery-results) associado a esta tarefa.

        Retorna ``None`` se o backend de resultados ainda não persistiu nada
        para esse ``task_id`` (ex.: tarefa ainda em ``PENDING``).
        """
        from django_celery_results.models import TaskResult

        return TaskResult.objects.filter(task_id=self.task_id).first()

    def update_status(self, save: bool = True, task_result=None) -> str:
        """Sincroniza ``status`` com o ``TaskResult`` mais recente da tarefa.

        Se o ``TaskResult`` ainda não existir (a tarefa não terminou ou o
        backend de resultados ainda não persistiu), o status atual é mantido.
        Retorna o status resultante (novo ou inalterado). Aceita um
        ``task_result`` já carregado para evitar uma consulta redundante
        (ver :meth:`as_status_payload`).
        """
        if task_result is None:
            task_result = self._get_task_result()
        if task_result is not None and task_result.status != self.status:
            self.status = task_result.status
            if save:
                self.save(update_fields=["status", "updated_at"])
        return self.status

    @property
    def is_finished(self) -> bool:
        """``True`` quando o status atual é terminal (sucesso, falha ou revogada)."""
        return self.status in FINISHED_STATES

    def get_traceback(self) -> Optional[str]:
        """Retorna o stacktrace bruto do ``TaskResult``, sem verificação de permissão.

        Uso interno / para chamadores que já validaram a permissão do usuário
        (ex.: um campo do admin já removido da tela para quem não tem acesso).
        Prefira :meth:`get_error_details` ao expor dados diretamente a um usuário.
        """
        task_result = self._get_task_result()
        return getattr(task_result, "traceback", None) if task_result else None

    def get_progress(self, task_result=None) -> Optional[dict[str, Any]]:
        """Retorna o dict de progresso publicado por um estado customizado.

        Quando uma task chama ``self.update_state(state="PROGRESS",
        meta={"percent": 42})``, o backend de resultados grava ``meta`` no
        campo ``result`` do ``TaskResult`` (serializado, normalmente como
        JSON). Este método decodifica esse valor e o retorna como ``dict``
        — ou ``None`` para estados padrão do Celery (``PENDING``,
        ``STARTED``, etc., que não carregam progresso) ou quando o valor não
        é um JSON/objeto decodificável.
        """
        if task_result is None:
            task_result = self._get_task_result()
        if task_result is None or task_result.status in _STANDARD_STATES:
            return None
        if task_result.content_type != "application/json" or not task_result.result:
            return None
        try:
            data = json.loads(task_result.result)
        except (TypeError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def get_error_details(self, user) -> dict[str, Any]:
        """Retorna os detalhes de erro da tarefa, respeitando a permissão do usuário.

        Superusuários e usuários com a permissão ``view_task_trace`` recebem o
        stacktrace completo em ``traceback``. Demais usuários recebem
        ``traceback=None`` e apenas a mensagem amigável configurada em
        :data:`django_celery_task_monitor.settings.FRIENDLY_ERROR_MESSAGE`.
        """
        task_result = self._get_task_result()
        result_text = getattr(task_result, "result", None) if task_result else None

        if not user_can_view_task_trace(user):
            return {"message": str(app_settings.FRIENDLY_ERROR_MESSAGE), "traceback": None}

        return {
            "message": result_text or str(app_settings.FRIENDLY_ERROR_MESSAGE),
            "traceback": self.get_traceback(),
        }

    def get_status_message(self) -> str:
        """Frase de status legível (ex.: "Tarefa em processamento há 12s.").

        Usada para o render inicial do painel ao vivo (:func:`get_urls`'s
        template ``task_status_panel.html``), antes do JavaScript assumir via
        polling. Note que, sem ``CELERY_TASK_TRACK_STARTED = True`` no
        projeto host, o Celery não registra quando a execução começou de
        fato — nesse caso a tarefa aparenta ficar "enfileirada" até o
        resultado final, mesmo já estando em execução (ver docs/configuration.rst).
        """
        task_result = self._get_task_result()
        self.update_status(task_result=task_result)
        started_at = getattr(task_result, "date_started", None) if task_result else None
        return _compose_status_message(
            self.status, started_at, self.get_progress(task_result=task_result)
        )

    def as_status_payload(self, user) -> dict[str, Any]:
        """Serializa o estado atual da tarefa para o endpoint REST de polling.

        Além do status "cru", inclui ``started_at`` (quando a execução
        realmente começou, segundo o ``TaskResult``), ``progress`` (dict de
        progresso, se a task publicou um) e ``message`` (frase pronta,
        equivalente à de :meth:`get_status_message`) — o JavaScript do
        plugin recompõe essa frase a cada segundo no cliente (para o relógio
        de tempo decorrido andar entre um poll e outro), mas ``message`` já
        serve pronta para qualquer outro consumidor do endpoint.
        """
        task_result = self._get_task_result()
        self.update_status(task_result=task_result)
        started_at = getattr(task_result, "date_started", None) if task_result else None
        progress = self.get_progress(task_result=task_result)
        payload: dict[str, Any] = {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "status_display": str(self.get_status_display()),
            "message": _compose_status_message(self.status, started_at, progress),
            "is_finished": self.is_finished,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": started_at.isoformat() if started_at else None,
            "progress": progress,
        }
        if self.status == FAILURE:
            payload["error"] = self.get_error_details(user)
        return payload
