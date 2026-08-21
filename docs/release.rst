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
5. Gere a distribuição:

   .. code-block:: bash

      python -m build

6. Publique no PyPI:

   .. code-block:: bash

      twine upload dist/*

7. Crie uma tag Git (``vX.Y.Z``) e uma release no GitHub apontando para ela.

Compatibilidade
==================

Mudanças que quebram a API pública (``TaskLog``, ``CeleryTaskMonitorMixin``,
template tags, endpoints REST, nomes de settings) exigem um bump de
``MAJOR`` e devem manter um caminho de migração sempre que viável — ver a
seção correspondente em ``CONTRIBUTING.md``.
