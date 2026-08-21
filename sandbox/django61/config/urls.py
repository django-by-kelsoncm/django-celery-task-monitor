"""URLconf raiz do sandbox em Django 6.1."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
