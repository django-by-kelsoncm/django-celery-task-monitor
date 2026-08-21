"""URLconf usado apenas pela suíte de testes."""

from django.contrib import admin
from django.urls import path

from django_celery_task_monitor.views import TaskStatusView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
]
