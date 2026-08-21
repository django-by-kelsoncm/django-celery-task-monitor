"""Testes de ``CeleryTaskMonitorMixin.start_task()``/``create_task_log()``.

Esses métodos existem para abstrair o boilerplate de registrar um
``TaskLog`` sempre que uma tarefa é disparada — não importa se isso
acontece em ``response_change``, numa ``action`` de changelist (uma chamada
por objeto do queryset) ou em qualquer outro lugar do ``ModelAdmin``.
"""

import pytest
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.urls import reverse

from django_celery_task_monitor.models import TaskLog

pytestmark = pytest.mark.django_db


def _admin_instance():
    from example_app.models import Relatorio

    return site._registry[Relatorio]


def _request_for(user):
    request = RequestFactory().post("/admin/example_app/relatorio/1/change/")
    request.user = user
    return request


def test_start_task_dispatches_and_creates_task_log(relatorio, django_user_model):
    from example_app.tasks import processar_relatorio

    user = django_user_model.objects.create_user(username="autor", password="x")  # noqa: S106
    request = _request_for(user)
    admin_instance = _admin_instance()

    task_log = admin_instance.start_task(request, relatorio, processar_relatorio, relatorio.id)

    assert isinstance(task_log, TaskLog)
    assert task_log.pk is not None
    assert task_log.content_object == relatorio
    assert task_log.object_id == str(relatorio.pk)
    assert task_log.started_by == user
    # Nome derivado automaticamente de `task.name`, sem precisar informar.
    assert task_log.task_name == "example_app.processar_relatorio"
    # CELERY_TASK_ALWAYS_EAGER=True nas settings de teste: a task já rodou.
    relatorio.refresh_from_db()
    assert relatorio.processado is True


def test_start_task_accepts_task_name_override(relatorio, django_user_model):
    from example_app.tasks import processar_relatorio

    user = django_user_model.objects.create_user(username="autor2", password="x")  # noqa: S106
    request = _request_for(user)
    admin_instance = _admin_instance()

    task_log = admin_instance.start_task(
        request, relatorio, processar_relatorio, relatorio.id, task_name="nome-customizado"
    )

    assert task_log.task_name == "nome-customizado"


def test_create_task_log_registers_an_already_dispatched_task(relatorio):
    admin_instance = _admin_instance()
    request = _request_for(None)

    task_log = admin_instance.create_task_log(
        request, relatorio, "task-id-ja-existente", task_name="minha_task"
    )

    assert task_log.task_id == "task-id-ja-existente"
    assert task_log.task_name == "minha_task"
    assert task_log.started_by is None


def test_changelist_action_starts_one_task_per_selected_object(
    client, django_user_model, relatorio
):
    from example_app.models import Relatorio

    outro = Relatorio.objects.create(nome="Segundo relatório")
    superuser = django_user_model.objects.create_superuser(
        username="root-action", password="senha-123", email="root-action@example.com"  # noqa: S106
    )
    client.force_login(superuser)

    url = reverse("admin:example_app_relatorio_changelist")
    response = client.post(
        url,
        {
            "action": "processar_selecionados_async",
            "_selected_action": [str(relatorio.pk), str(outro.pk)],
        },
        follow=True,
    )

    assert response.status_code == 200
    assert TaskLog.objects.filter(object_id=str(relatorio.pk)).count() == 1
    assert TaskLog.objects.filter(object_id=str(outro.pk)).count() == 1
    for obj in (relatorio, outro):
        obj.refresh_from_db()
        assert obj.processado is True
