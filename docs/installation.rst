============
Instalação
============

Requisitos
==========

- Django 4.2+
- Celery 5.x
- Python 3.10+
- `django-celery-results <https://github.com/celery/django-celery-results>`_ >= 2.5

``django-celery-results`` é a única dependência direta do plugin — é dela que
vem o modelo ``TaskResult`` usado para consultar o resultado real das
tarefas Celery.

Instalando o pacote
====================

.. code-block:: bash

   pip install django-celery-task-monitor

Registrando as apps
====================

Adicione as duas apps ao ``INSTALLED_APPS`` do seu projeto:

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       "django_celery_results",
       "django_celery_task_monitor",
   ]

Rodando as migrações
=====================

.. code-block:: bash

   python manage.py migrate

Isso cria a tabela de ``TaskLog`` e registra as permissões
``view_tasklog``, ``change_tasklog``, ``delete_tasklog`` (padrão do Django
para qualquer modelo) e ``view_task_trace`` (customizada pelo plugin, ver
:doc:`permissions`).

Próximo passo
==============

Veja :doc:`configuration` para as configurações opcionais, ou vá direto para
:doc:`usage` para o exemplo mínimo de uso no admin.
