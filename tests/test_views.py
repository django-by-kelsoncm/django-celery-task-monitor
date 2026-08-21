"""Testes de ``django_celery_task_monitor.views.TaskStatusView``."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _url(task_id: str) -> str:
    return reverse("task-status", args=[task_id])


def test_task_status_view_returns_payload_for_authenticated_user(
    client, django_user_model, make_task_log
):
    user = django_user_model.objects.create_user(username="viewer", password="x")  # noqa: S106
    make_task_log(task_id="view-1", status="SUCCESS", result='"ok"')
    client.force_login(user)

    response = client.get(_url("view-1"))

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "view-1"
    assert data["status"] == "SUCCESS"


def test_task_status_view_requires_login(client, make_task_log):
    make_task_log(task_id="view-2", status="PENDING")

    response = client.get(_url("view-2"))

    assert response.status_code == 302  # LoginRequiredMixin redireciona para o login


def test_task_status_view_returns_404_for_unknown_task(client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer2", password="x")  # noqa: S106
    client.force_login(user)

    response = client.get(_url("does-not-exist"))

    assert response.status_code == 404
