"""Testes do modelo ``TaskLog``."""

import json

import pytest
from django.contrib.contenttypes.models import ContentType
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

pytestmark = pytest.mark.django_db


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
