"""Testes de ``django_celery_task_monitor.permissions``."""

import pytest
from django.contrib.auth.models import AnonymousUser

from django_celery_task_monitor.permissions import user_can_view_task_trace

pytestmark = pytest.mark.django_db


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
