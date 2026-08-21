"""URLconf raiz do sandbox em Django 5.2."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
