"""Testes de ``django_celery_task_monitor``."""

import json

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite, site
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from django_celery_task_monitor.models import (
    FAILURE,
    PENDING,
    PROGRESS,
    REVOKED,
    STARTED,
    SUCCESS,
    TaskLog,
    _format_duration,
)
from django_celery_task_monitor.permissions import user_can_view_task_trace
from django_celery_task_monitor.templatetags.task_monitor_tags import (
    task_monitor_static_css_url,
    task_monitor_static_url,
    task_poll_script,
    task_status_badge,
    task_status_panel,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# TaskLog (model)
# ---------------------------------------------------------------------------


def test_create_task_log_links_to_any_model(relatorio):
    task_log = TaskLog.objects.create(
        content_type=ContentType.objects.get_for_model(relatorio),
        object_id=str(relatorio.pk),
        task_id="abc-123",
        task_name="example_app.processar_relatorio",
    )

    assert task_log.content_object == relatorio
    assert task_log.status == PENDING
    assert not task_log.is_finished


def test_update_status_syncs_from_task_result(make_task_log):
    task_log = make_task_log(task_id="task-success", status=PENDING)

    from django_celery_results.models import TaskResult

    TaskResult.objects.create(task_id="task-success", status=SUCCESS, result='"ok"')

    new_status = task_log.update_status()

    task_log.refresh_from_db()
    assert new_status == SUCCESS
    assert task_log.status == SUCCESS
    assert task_log.is_finished


def test_update_status_keeps_current_status_without_task_result(relatorio):
    task_log = TaskLog.objects.create(
        content_type=ContentType.objects.get_for_model(relatorio),
        object_id=str(relatorio.pk),
        task_id="no-result-yet",
    )

    assert task_log.update_status() == PENDING


def test_get_error_details_hides_traceback_for_regular_user(make_task_log, regular_user):
    task_log = make_task_log(
        task_id="task-fail-1", status=FAILURE, traceback="Traceback (most recent call last): ..."
    )

    details = task_log.get_error_details(regular_user)

    from django_celery_task_monitor import settings as app_settings

    assert details["traceback"] is None
    assert details["message"] == str(app_settings.FRIENDLY_ERROR_MESSAGE)


def test_get_error_details_shows_traceback_for_permitted_user(
    make_task_log, user_with_trace_permission
):
    task_log = make_task_log(
        task_id="task-fail-2", status=FAILURE, traceback="Traceback (most recent call last): ..."
    )

    details = task_log.get_error_details(user_with_trace_permission)

    assert details["traceback"] == "Traceback (most recent call last): ..."


def test_get_error_details_shows_traceback_for_superuser(make_task_log, django_user_model):
    superuser = django_user_model.objects.create_superuser(
        username="admin", password="senha-123", email="admin@example.com"  # noqa: S106
    )
    task_log = make_task_log(task_id="task-fail-3", status=FAILURE, traceback="boom")

    details = task_log.get_error_details(superuser)

    assert details["traceback"] == "boom"


def test_as_status_payload_includes_error_only_on_failure(make_task_log, relatorio):
    ok_log = make_task_log(task_id="task-ok", status=SUCCESS, result='"done"')
    payload = ok_log.as_status_payload(None)
    assert "error" not in payload
    assert payload["is_finished"] is True

    failed_log = make_task_log(task_id="task-bad", status=FAILURE, traceback="oops")
    payload = failed_log.as_status_payload(None)
    assert "error" in payload
    assert payload["error"]["traceback"] is None  # user=None não tem permissão


def test_get_progress_returns_none_for_standard_states(make_task_log):
    task_log = make_task_log(task_id="task-started", status=STARTED, result=None)
    assert task_log.get_progress() is None


def test_get_progress_decodes_json_meta_from_custom_state(make_task_log):
    task_log = make_task_log(
        task_id="task-progress", status=PROGRESS, result=json.dumps({"percent": 42})
    )
    assert task_log.get_progress() == {"percent": 42}


def test_get_progress_ignores_non_dict_or_undecodable_result(make_task_log):
    not_a_dict = make_task_log(task_id="task-progress-list", status=PROGRESS, result="[1, 2]")
    assert not_a_dict.get_progress() is None

    not_json = make_task_log(task_id="task-progress-bad", status=PROGRESS, result="not json")
    assert not_json.get_progress() is None


def test_as_status_payload_includes_started_at_and_progress(make_task_log):
    started_at = timezone.now()
    task_log = make_task_log(
        task_id="task-running",
        status=PROGRESS,
        result=json.dumps({"percent": 50}),
        date_started=started_at,
    )

    payload = task_log.as_status_payload(None)

    assert payload["started_at"] == started_at.isoformat()
    assert payload["progress"] == {"percent": 50}
    assert "processamento" in payload["message"].lower()


def test_get_status_message_reflects_lifecycle(make_task_log, relatorio):
    queued = TaskLog.objects.create(
        content_type=ContentType.objects.get_for_model(relatorio),
        object_id=str(relatorio.pk),
        task_id="task-queued",
    )
    assert queued.get_status_message() == "Tarefa enfileirada."

    running = make_task_log(task_id="task-running-2", status=STARTED, date_started=timezone.now())
    assert "processamento" in running.get_status_message().lower()

    done = make_task_log(task_id="task-done", status=SUCCESS, result='"ok"')
    assert done.get_status_message() == "Tarefa finalizada com sucesso."

    failed = make_task_log(task_id="task-failed", status=FAILURE, traceback="boom")
    assert failed.get_status_message() == "Tarefa finalizada com erro."


def test_get_status_message_for_revoked_task(make_task_log):
    revoked = make_task_log(task_id="task-revoked")
    revoked.status = REVOKED
    revoked.save(update_fields=["status"])

    assert revoked.get_status_message() == "Tarefa cancelada."


def test_get_progress_returns_none_when_content_type_is_not_json(make_task_log):
    task_log = make_task_log(
        task_id="task-progress-textplain",
        status=PROGRESS,
        result="percent: 50",
        content_type="text/plain",
    )

    assert task_log.get_progress() is None


@pytest.mark.parametrize(
    ("total_seconds", "expected"),
    [
        (0, "0s"),
        (45, "45s"),
        (65, "1min 5s"),
        (3725, "1h 2min 5s"),
    ],
)
def test_format_duration(total_seconds, expected):
    assert _format_duration(total_seconds) == expected


# ---------------------------------------------------------------------------
# django_celery_task_monitor.permissions
# ---------------------------------------------------------------------------


def test_anonymous_user_cannot_view_trace():
    assert user_can_view_task_trace(AnonymousUser()) is False


def test_none_user_cannot_view_trace():
    assert user_can_view_task_trace(None) is False


def test_regular_user_without_permission_cannot_view_trace(regular_user):
    assert user_can_view_task_trace(regular_user) is False


def test_user_with_permission_can_view_trace(user_with_trace_permission):
    assert user_can_view_task_trace(user_with_trace_permission) is True


def test_superuser_can_always_view_trace(django_user_model):
    superuser = django_user_model.objects.create_superuser(
        username="root", password="senha-123", email="root@example.com"  # noqa: S106
    )
    assert user_can_view_task_trace(superuser) is True


# ---------------------------------------------------------------------------
# Template tags
# ---------------------------------------------------------------------------


def test_task_status_badge_tag_with_task_log(make_task_log):
    task_log = make_task_log(task_id="tag-badge-1", status="SUCCESS", result='"ok"')

    context = task_status_badge(task_log, poll_url="/poll/", poll_interval=1000)

    assert context["task_log"] == task_log
    assert context["status"] == "SUCCESS"
    assert context["poll_url"] == "/poll/"
    assert context["poll_interval"] == 1000


def test_task_status_badge_tag_without_task_log():
    context = task_status_badge(None)

    assert context["task_log"] is None
    assert context["status"] is None
    assert context["status_display"] is None


def test_task_status_panel_tag_with_task_log(make_task_log):
    task_log = make_task_log(task_id="tag-panel-1", status="SUCCESS", result='"ok"')

    context = task_status_panel(task_log)

    assert context["message"] == "Tarefa finalizada com sucesso."


def test_task_status_panel_tag_without_task_log():
    context = task_status_panel(None)

    assert context["task_log"] is None
    assert context["message"] is None


def test_task_monitor_static_url():
    assert task_monitor_static_url().endswith("task-poll.js")


def test_task_monitor_static_css_url():
    assert task_monitor_static_css_url().endswith("task-monitor.css")


def test_task_poll_script_default_selector():
    html = task_poll_script()

    assert "task-poll.js" in html
    assert ".task-status-badge" in html
    assert "TaskPoll.init" in html


def test_task_poll_script_custom_selector_and_interval():
    html = task_poll_script(".minha-classe", poll_interval=1234)

    assert ".minha-classe" in html
    assert "1234" in html


def test_templatetags_load_and_render_in_a_real_template(make_task_log):
    task_log = make_task_log(task_id="tag-render-1", status="SUCCESS", result='"ok"')
    template = Template(
        "{% load task_monitor_tags %}"
        "{% task_status_badge task_log %}"
        "{% task_status_panel task_log %}"
        "{% task_poll_script %}"
    )

    rendered = template.render(Context({"task_log": task_log}))

    assert "task-status-badge" in rendered
    assert "task-status-panel" in rendered
    assert "TaskPoll.init" in rendered


# ---------------------------------------------------------------------------
# TaskStatusView
# ---------------------------------------------------------------------------


def _view_url(task_id: str) -> str:
    return reverse("task-status", args=[task_id])


def test_task_status_view_returns_payload_for_authenticated_user(
    client, django_user_model, make_task_log
):
    user = django_user_model.objects.create_user(username="viewer", password="x")  # noqa: S106
    make_task_log(task_id="view-1", status="SUCCESS", result='"ok"')
    client.force_login(user)

    response = client.get(_view_url("view-1"))

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "view-1"
    assert data["status"] == "SUCCESS"


def test_task_status_view_requires_login(client, make_task_log):
    make_task_log(task_id="view-2", status="PENDING")

    response = client.get(_view_url("view-2"))

    assert response.status_code == 302  # LoginRequiredMixin redireciona para o login


def test_task_status_view_returns_404_for_unknown_task(client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer2", password="x")  # noqa: S106
    client.force_login(user)

    response = client.get(_view_url("does-not-exist"))

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# CeleryTaskMonitorMixin.start_task()/create_task_log() (admin)
#
# Esses métodos existem para abstrair o boilerplate de registrar um
# ``TaskLog`` sempre que uma tarefa é disparada — não importa se isso
# acontece em ``response_change``, numa ``action`` de changelist (uma chamada
# por objeto do queryset) ou em qualquer outro lugar do ``ModelAdmin``.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Endpoint REST de polling e admin views (changelist/change view, TaskLog
# admin)
# ---------------------------------------------------------------------------


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
    from django_celery_results.models import TaskResult

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
