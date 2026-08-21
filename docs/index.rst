=============================
django-celery-task-monitor
=============================

Monitoramento de tarefas Celery no Django Admin, com polling via REST.

.. toctree::
   :maxdepth: 2
   :caption: Sumário de Conteúdos:

   installation
   configuration
   usage
   advanced
   api-reference
   javascript
   permissions
   example-project
   faq
   development
   release

Funcionalidades
===============

- Modelo ``TaskLog``, vinculado a qualquer modelo do projeto host via ``GenericForeignKey``
- Mixin ``CeleryTaskMonitorMixin`` para qualquer ``ModelAdmin``, com coluna de status e polling automático
- Endpoint REST de polling registrado por ``ModelAdmin`` (``get_urls()``), sem código extra
- JavaScript modular e auto-contido (``task-poll.js``), sem dependências externas
- Controle de permissão granular (``view_task_trace``) para exibir ou ocultar stacktraces completos
- Internacionalizado (``pt-BR``/``en``)

Links Rápidos
=============

- :doc:`Instalação <installation>`
- :doc:`Configuração <configuration>`
- :doc:`Uso Básico <usage>`
- :doc:`Uso Avançado <advanced>`
- :doc:`Referência da API <api-reference>`
- :doc:`JavaScript <javascript>`
- :doc:`Permissões <permissions>`
- :doc:`Projeto de Exemplo <example-project>`
- :doc:`FAQ <faq>`
- :doc:`Desenvolvimento <development>`
- :doc:`Processo de Release <release>`
