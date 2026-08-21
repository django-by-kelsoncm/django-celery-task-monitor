"""Fixtures compartilhadas pela suíte de testes."""

from __future__ import annotations

import pytest
from celery import current_app
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

# example_app.tasks usa @shared_task, que se vincula à app Celery "atual"
# (current_app) quando nenhuma app dedicada foi criada — diferente de um
# projeto Django real, onde example_project/celery.py faz
# `app.config_from_object("django.conf:settings", namespace="CELERY")` na
# inicialização. Sem este passo aqui, os CELERY_* de tests/settings.py
# (CELERY_TASK_ALWAYS_EAGER, CELERY_BROKER_URL, ...) nunca chegam à app de
# verdade, e qualquer `.delay()` tenta abrir uma conexão AMQP de verdade.
current_app.config_from_object("django.conf:settings", namespace="CELERY")


@pytest.fixture
def relatorio(db):
    from example_app.models import Relatorio

    return Relatorio.objects.create(nome="Relatório de teste")


@pytest.fixture
def regular_user(db):
    return get_user_model().objects.create_user(
        username="joao", password="senha-123", is_staff=True  # noqa: S106
    )


@pytest.fixture
def user_with_trace_permission(db):
    from django.contrib.auth.models import Permission

    user = get_user_model().objects.create_user(
        username="maria", password="senha-123", is_staff=True  # noqa: S106
    )
    permission = Permission.objects.get(
        content_type__app_label="django_celery_task_monitor",
        codename="view_task_trace",
    )
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def make_task_log(db, relatorio):
    """Factory que cria um ``TaskLog`` (e opcionalmente um ``TaskResult``) para os testes."""

    def _make(
        task_id="task-123",
        status="PENDING",
        traceback=None,
        result=None,
        date_started=None,
        content_type="application/json",
        **kwargs,
    ):
        from django_celery_task_monitor.models import TaskLog

        task_log = TaskLog.objects.create(
            content_type=ContentType.objects.get_for_model(relatorio),
            object_id=str(relatorio.pk),
            task_id=task_id,
            task_name=kwargs.pop("task_name", "example_app.processar_relatorio"),
            status=status,
            **kwargs,
        )
        if status != "PENDING":
            from django_celery_results.models import TaskResult

            TaskResult.objects.create(
                task_id=task_id,
                status=status,
                traceback=traceback,
                result=result,
                date_started=date_started,
                content_type=content_type,
                content_encoding="utf-8",
            )
        return task_log

    return _make
