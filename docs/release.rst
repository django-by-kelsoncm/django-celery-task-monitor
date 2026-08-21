=========
Release
=========

Versionamento
===============

O projeto segue `Semantic Versioning <https://semver.org/lang/pt-BR/>`_
(``MAJOR.MINOR.PATCH``). A versão vive em dois lugares que precisam ficar em
sincronia:

- ``django_celery_task_monitor/__init__.py`` (``__version__``)
- ``pyproject.toml`` (``[project].version``)

Checklist de release
=======================

1. Atualize ``__version__`` e ``[project].version``.
2. Rode a suíte completa: ``pytest``, ``black --check``, ``flake8``, ``mypy``.
3. Se alguma string traduzível mudou, regenere e recompile as traduções
   (``makemessages`` + ``compilemessages``, ver :doc:`development`) e
   confira que os ``.mo`` atualizados foram commitados — quem instala via
   pip não roda ``compilemessages``, então o ``.mo`` versionado é o que
   efetivamente é publicado.
4. Atualize o changelog (se/quando o projeto adotar um ``CHANGELOG.md``).
5. Confira localmente antes de publicar de verdade (o CI não builda o
   pacote, só testa/lint):

   .. code-block:: bash

      python -m build
      twine check dist/*

6. Dê push no ``main`` e crie uma *release* no GitHub (com uma tag
   ``vX.Y.Z``) apontando para o commit da nova versão. O workflow
   ``.github/workflows/publish.yml`` dispara automaticamente no evento
   ``release: published``: builda o pacote, roda ``twine check`` e publica
   no PyPI via *Trusted Publisher* (OIDC) — sem token armazenado no GitHub.

   Pré-requisito (uma vez só, feito no site do PyPI, não pelo CI):
   registrar este repositório como *trusted publisher* do projeto
   ``django-celery-task-monitor`` em
   `pypi.org → seu projeto → Publishing <https://pypi.org/manage/account/publishing/>`_,
   apontando para o workflow ``publish.yml`` deste repositório.

Compatibilidade
==================

Mudanças que quebram a API pública (``TaskLog``, ``CeleryTaskMonitorMixin``,
template tags, endpoints REST, nomes de settings) exigem um bump de
``MAJOR`` e devem manter um caminho de migração sempre que viável — ver a
seção correspondente em ``CONTRIBUTING.md``.
