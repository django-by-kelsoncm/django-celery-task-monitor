"""Testes do endpoint REST de polling exposto por ``CeleryTaskMonitorMixin``."""

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _poll_url(task_id: str) -> str:
    return reverse("admin:example_app_relatorio_celery_task_status", args=[task_id])


def test_polling_endpoint_returns_task_status(client, django_user_model, make_task_log):
    staff = django_user_model.objects.create_user(
        username="staff", password="senha-123", is_staff=True  # noqa: S106
    )
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="example_app", codename="view_relatorio")
    )
    make_task_log(task_id="poll-1", status="SUCCESS", result='"ok"')
    client.force_login(staff)

    response = client.get(_poll_url("poll-1"))

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "poll-1"
    assert data["status"] == "SUCCESS"
    assert data["is_finished"] is True


def test_polling_endpoint_requires_view_permission(client, django_user_model, make_task_log):
    staff_no_perm = django_user_model.objects.create_user(
        username="no-perm", password="senha-123", is_staff=True  # noqa: S106
    )
    make_task_log(task_id="poll-2", status="PENDING")
    client.force_login(staff_no_perm)

    response = client.get(_poll_url("poll-2"))

    assert response.status_code == 403


def test_polling_endpoint_returns_404_for_unknown_task(client, django_user_model):
    staff = django_user_model.objects.create_superuser(
        username="root2", password="senha-123", email="root2@example.com"  # noqa: S106
    )
    client.force_login(staff)

    response = client.get(_poll_url("does-not-exist"))

    assert response.status_code == 404


def test_polling_endpoint_requires_login(client, make_task_log):
    make_task_log(task_id="poll-3", status="PENDING")

    response = client.get(_poll_url("poll-3"))

    # admin_view() redireciona usuários não autenticados para o login.
    assert response.status_code in (302, 403)


def test_changelist_renders_task_status_badge(client, django_user_model, make_task_log, relatorio):
    superuser = django_user_model.objects.create_superuser(
        username="root3", password="senha-123", email="root3@example.com"  # noqa: S106
    )
    make_task_log(task_id="poll-4", status="STARTED")
    client.force_login(superuser)

    url = reverse("admin:example_app_relatorio_changelist")
    response = client.get(url)

    assert response.status_code == 200
    assert b"task-status-badge" in response.content


def test_tasklog_admin_hides_traceback_from_unpermitted_user(client, regular_user, make_task_log):
    task_log = make_task_log(task_id="poll-5", status="FAILURE", traceback="secret trace")
    regular_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="django_celery_task_monitor", codename="view_tasklog"
        )
    )
    client.force_login(regular_user)

    url = reverse("admin:django_celery_task_monitor_tasklog_change", args=[task_log.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert b"secret trace" not in response.content


def test_tasklog_admin_shows_traceback_to_permitted_user(
    client, user_with_trace_permission, make_task_log
):
    task_log = make_task_log(task_id="poll-6", status="FAILURE", traceback="secret trace")
    user_with_trace_permission.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="django_celery_task_monitor", codename="view_tasklog"
        )
    )
    client.force_login(user_with_trace_permission)

    url = reverse("admin:django_celery_task_monitor_tasklog_change", args=[task_log.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert b"secret trace" in response.content
