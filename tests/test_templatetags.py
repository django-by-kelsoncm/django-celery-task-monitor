"""Testes das template tags de ``django_celery_task_monitor``."""

import pytest
from django.template import Context, Template

from django_celery_task_monitor.templatetags.task_monitor_tags import (
    task_monitor_static_css_url,
    task_monitor_static_url,
    task_poll_script,
    task_status_badge,
    task_status_panel,
)

pytestmark = pytest.mark.django_db


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
