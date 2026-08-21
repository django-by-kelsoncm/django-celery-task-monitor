===================
Projeto de Exemplo
===================

O repositório inclui um projeto Django mínimo em ``example/`` que demonstra
o uso completo do plugin: um ``ModelAdmin`` (``RelatorioAdmin``) usando
``CeleryTaskMonitorMixin`` exatamente como descrito em :doc:`usage`, com uma
tarefa Celery de exemplo (``example_app.tasks.processar_relatorio``) e o
botão "Processar (assíncrono)" no formulário de edição.

Estrutura
===========

.. code-block:: text

   example/
   ├── manage.py
   ├── example_project/
   │   ├── settings.py      # Django + Celery, CELERY_TASK_ALWAYS_EAGER=True
   │   ├── celery.py
   │   ├── urls.py
   │   └── wsgi.py
   └── example_app/
       ├── models.py        # Relatorio
       ├── admin.py         # RelatorioAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin)
       ├── tasks.py         # processar_relatorio
       └── templates/admin/example_app/relatorio/change_form.html

Rodando localmente
=====================

.. code-block:: bash

   git clone https://github.com/django-by-kelsoncm/django-celery-task-monitor.git
   cd django-celery-task-monitor
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   cd example
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver

Acesse ``http://localhost:8000/admin/``, crie um "Relatório" e clique em
"Processar (assíncrono)" — o badge de status muda de "Pendente" para
"Concluída" sozinho, via polling, sem recarregar a página.

Por que ``CELERY_TASK_ALWAYS_EAGER``?
========================================

O exemplo roda sem worker/broker de verdade: as tarefas executam de forma
síncrona no mesmo processo do ``runserver``. Para isso funcionar com o
monitor de tarefas (que depende do backend de resultados), o exemplo também
ativa ``CELERY_TASK_STORE_EAGER_RESULT = True`` — sem essa flag, tarefas
eager não persistem o ``TaskResult`` e o polling nunca sairia de
``PENDING`` (ver a nota em :doc:`configuration`). Em produção, aponte
``CELERY_BROKER_URL`` para Redis/RabbitMQ e rode um worker de verdade.

A suíte de testes (``tests/``) reaproveita ``example_app.Relatorio`` como
modelo alvo do ``GenericForeignKey`` de ``TaskLog``, em vez de duplicar um
modelo de teste — ver :doc:`development`.
