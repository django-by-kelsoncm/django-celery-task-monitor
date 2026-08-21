===============
Desenvolvimento
===============

Configurando o ambiente
==========================

.. code-block:: bash

   git clone https://github.com/django-by-kelsoncm/django-celery-task-monitor.git
   cd django-celery-task-monitor
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   pre-commit install
   pre-commit install --hook-type pre-push

Rodando os testes
=====================

.. code-block:: bash

   pytest

A suíte usa ``pytest-django`` com ``tests/settings.py``, que reaproveita o
app ``example_app`` (pasta ``example/``) como modelo alvo do
``GenericForeignKey`` de ``TaskLog`` — ver :doc:`example-project`.

Qualidade de código
======================

.. code-block:: bash

   black django_celery_task_monitor tests example
   flake8 django_celery_task_monitor tests example
   mypy django_celery_task_monitor

Todos os três rodam no CI (GitHub Actions, ``.github/workflows/ci.yml``)
contra a matriz de Python (3.10–3.12) e Django (4.2–5.1) suportada.

pre-commit
============

O projeto usa hooks de ``pre-commit`` (config em
``.pre-commit-config.yaml``):

- **pre-commit** (a cada ``git commit``): espaço em branco à direita,
  fixador de fim de arquivo, verificação de YAML, arquivos grandes
  acidentais, conflitos de merge não resolvidos, ``black`` e ``flake8``.
- **pre-push** (a cada ``git push``, mais lento): ``mypy`` e ``pytest``.

Os hooks locais (``mypy``/``pytest``) usam ``language: system`` — rodam com
o Python/venv já ativo no seu shell, não um ambiente isolado do
``pre-commit``. Para testar sem commitar/dar push:

.. code-block:: bash

   pre-commit run --all-files
   pre-commit run --all-files --hook-stage pre-push

Traduções
===========

.. code-block:: bash

   cd django_celery_task_monitor
   django-admin makemessages -l pt_BR -l en --no-location --no-obsolete
   # edite os .po gerados preenchendo os msgstr que faltam
   django-admin compilemessages

Construindo esta documentação
=================================

.. code-block:: bash

   pip install -e ".[docs]"
   cd docs
   make html
   # ou, no Windows: make.bat html

O HTML gerado fica em ``docs/_build/html/``.

Veja também o arquivo ``CONTRIBUTING.md`` na raiz do repositório para o
fluxo completo de contribuição (PRs, issues, política de breaking changes).
