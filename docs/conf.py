# Configuration file for Sphinx documentation of django-celery-task-monitor
import os
import sys

# Ensure package root is in Python path
sys.path.insert(0, os.path.abspath(".."))

# autodoc precisa importar django_celery_task_monitor.*, e vários desses
# módulos leem django.conf.settings no import (ex.: settings.py, models.py).
# Reaproveita as settings de teste do próprio projeto, já preparadas para
# rodar sem infraestrutura externa.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
import django  # noqa: E402

django.setup()

import django_docs_theme  # noqa: E402

project = "django-celery-task-monitor"
copyright = "2026, Kelson C. Medeiros"
author = "Kelson C. Medeiros"
release = "0.1.0"
language = "pt_BR"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "django_docs_theme",
]

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "django_docs_theme"
html_theme_path = [django_docs_theme.get_html_theme_path()]

html_theme_options = {
    "project_name": "django-celery-task-monitor",
    "tagline": "Monitoramento de tarefas Celery no Django Admin, com polling via REST",
    "github_url": "https://github.com/django-by-kelsoncm/django-celery-task-monitor",
    "github_repo": "django-by-kelsoncm/django-celery-task-monitor",
    "github_version": "main",
    "doc_path": "docs/",
    "show_edit_on_github": True,
    "navigation_links": (
        "Início|index.html, Instalação|installation.html, "
        "Configuração|configuration.html, Uso Básico|usage.html, "
        "Uso Avançado|advanced.html, Referência da API|api-reference.html, "
        "JavaScript|javascript.html, Permissões|permissions.html, "
        "Projeto de Exemplo|example-project.html, FAQ|faq.html, "
        "Desenvolvimento|development.html, Release|release.html, "
        "GitHub|https://github.com/django-by-kelsoncm/django-celery-task-monitor"
    ),
}

html_static_path = []
