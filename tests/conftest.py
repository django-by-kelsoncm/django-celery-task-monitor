"""Fixtures compartilhadas pela suíte de testes."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType


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

    def _make(task_id="task-123", status="PENDING", traceback=None, result=None, **kwargs):
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
            )
        return task_log

    return _make
