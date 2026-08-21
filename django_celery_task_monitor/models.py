"""Modelo ``TaskLog``: vincula tarefas Celery a qualquer instância de modelo Django.

O vínculo usa ``GenericForeignKey`` para que o plugin funcione com qualquer
modelo do projeto host, sem acoplamento a apps ou nomes específicos.
"""

from __future__ import annotations

from typing import Any, Optional

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from . import settings as app_settings
from .permissions import user_can_view_task_trace

# Estados possíveis de uma tarefa Celery. Espelham ``celery.states`` para que
# este módulo não precise importar o pacote ``celery`` diretamente.
PENDING = "PENDING"
STARTED = "STARTED"
RETRY = "RETRY"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
REVOKED = "REVOKED"

STATUS_CHOICES = [
    (PENDING, _("Pendente")),
    (STARTED, _("Em execução")),
    (RETRY, _("Repetindo")),
    (SUCCESS, _("Concluída")),
    (FAILURE, _("Falhou")),
    (REVOKED, _("Revogada")),
]

#: Estados finais — a tarefa não deve mais mudar de status a partir daqui.
FINISHED_STATES = frozenset({SUCCESS, FAILURE, REVOKED})


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

    def update_status(self, save: bool = True) -> str:
        """Sincroniza ``status`` com o ``TaskResult`` mais recente da tarefa.

        Se o ``TaskResult`` ainda não existir (a tarefa não terminou ou o
        backend de resultados ainda não persistiu), o status atual é mantido.
        Retorna o status resultante (novo ou inalterado).
        """
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

    def as_status_payload(self, user) -> dict[str, Any]:
        """Serializa o estado atual da tarefa para o endpoint REST de polling."""
        self.update_status()
        payload: dict[str, Any] = {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "status_display": str(self.get_status_display()),
            "is_finished": self.is_finished,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.status == FAILURE:
            payload["error"] = self.get_error_details(user)
        return payload
