"""Testes do endpoint REST de polling exposto por ``CeleryTaskMonitorMixin``."""

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite, site
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


def test_change_view_panel_reflects_status_after_sync_not_stale_cache(
    client, django_user_model, relatorio
):
    """Regressão: a TaskLog criada com status cacheado desatualizado (ex.: o
    default PENDING, gravado no instante em que a task foi disparada) deve
    aparecer no painel já com o status/CSS SINCRONIZADOS com o TaskResult
    real — não com uma mistura de "classe CSS antiga + mensagem nova" (bug
    de ordenação: get_status_message() atualiza task_log.status como efeito
    colateral, e o `status` do contexto precisa ser lido depois disso).
    """
    from django.contrib.contenttypes.models import ContentType
    from django_celery_results.models import TaskResult

    from django_celery_task_monitor.models import TaskLog

    task_log = TaskLog.objects.create(
        content_type=ContentType.objects.get_for_model(relatorio),
        object_id=str(relatorio.pk),
        task_id="stale-cache-task",
        task_name="example_app.processar_relatorio",
    )
    assert task_log.status == "PENDING"  # valor cacheado no momento da criação
    TaskResult.objects.create(
        task_id="stale-cache-task",
        status="SUCCESS",
        result='"ok"',
        content_type="application/json",
        content_encoding="utf-8",
    )

    superuser = django_user_model.objects.create_superuser(
        username="root-stale", password="senha-123", email="root-stale@example.com"  # noqa: S106
    )
    client.force_login(superuser)

    url = reverse("admin:example_app_relatorio_change", args=[relatorio.pk])
    response = client.get(url)
    content = response.content.decode()

    assert 'data-status="SUCCESS"' in content
    assert "task-status-panel--success" in content
    assert "Tarefa finalizada com sucesso." in content
    assert 'data-status="PENDING"' not in content


def test_change_view_renders_live_status_panel(client, django_user_model, make_task_log, relatorio):
    superuser = django_user_model.objects.create_superuser(
        username="root4", password="senha-123", email="root4@example.com"  # noqa: S106
    )
    make_task_log(task_id="poll-panel", status="SUCCESS", result='"ok"')
    client.force_login(superuser)

    url = reverse("admin:example_app_relatorio_change", args=[relatorio.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert b"task-status-panel" in response.content
    assert "Tarefa finalizada com sucesso.".encode() in response.content


def test_add_view_does_not_render_status_panel(client, django_user_model):
    superuser = django_user_model.objects.create_superuser(
        username="root5", password="senha-123", email="root5@example.com"  # noqa: S106
    )
    client.force_login(superuser)

    url = reverse("admin:example_app_relatorio_add")
    response = client.get(url)

    assert response.status_code == 200
    assert b"task-status-panel" not in response.content


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


def test_tasklog_changelist_renders_status_badge(client, django_user_model, make_task_log):
    superuser = django_user_model.objects.create_superuser(
        username="root-tasklog-cl",
        password="senha-123",
        email="root-tasklog-cl@example.com",  # noqa: S106
    )
    make_task_log(task_id="poll-cl", status="SUCCESS", result='"ok"')
    client.force_login(superuser)

    url = reverse("admin:django_celery_task_monitor_tasklog_changelist")
    response = client.get(url)

    assert response.status_code == 200
    assert b"task-status-badge" in response.content


def test_tasklog_admin_shows_dash_for_non_failure_message_and_traceback(
    client, django_user_model, make_task_log
):
    """``friendly_message``/``full_traceback`` mostram "—" fora do estado FAILURE."""
    superuser = django_user_model.objects.create_superuser(
        username="root-nonfail",
        password="senha-123",
        email="root-nonfail@example.com",  # noqa: S106
    )
    task_log = make_task_log(task_id="poll-nonfail", status="SUCCESS", result='"ok"')
    client.force_login(superuser)

    url = reverse("admin:django_celery_task_monitor_tasklog_change", args=[task_log.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert task_log.status != "FAILURE"
    assert "—".encode() in response.content


def test_celery_task_field_custom_name_creates_renderer(relatorio):
    from django_celery_task_monitor.admin import CeleryTaskMonitorMixin

    class CustomFieldAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
        celery_task_field = "status_customizado"

    admin_instance = CustomFieldAdmin(type(relatorio), AdminSite())

    assert hasattr(admin_instance, "status_customizado")
    renderer = admin_instance.status_customizado
    assert renderer.short_description == "Status da Tarefa"
    assert renderer(relatorio) == "—"


def test_task_status_column_shows_dash_when_object_has_no_task_log(relatorio):
    admin_instance = site._registry[type(relatorio)]

    assert admin_instance.task_status_column(relatorio) == "—"


def test_change_view_has_no_panel_when_object_has_no_task_log(client, django_user_model, relatorio):
    superuser = django_user_model.objects.create_superuser(
        username="root-no-task",
        password="senha-123",
        email="root-no-task@example.com",  # noqa: S106
    )
    client.force_login(superuser)

    url = reverse("admin:example_app_relatorio_change", args=[relatorio.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert b"task-status-panel" not in response.content
