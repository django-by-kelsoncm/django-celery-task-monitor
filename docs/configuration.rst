==============
Configuração
==============

Todas as configurações do plugin são opcionais — os defaults abaixo já
funcionam para a maioria dos projetos. Definidas em
``django_celery_task_monitor/settings.py`` e lidas do ``settings.py`` do
projeto host.

``CELERY_TASK_MONITOR_POLL_INTERVAL``
======================================

Intervalo padrão (em milissegundos) usado pelo JavaScript de polling quando
o ``ModelAdmin`` não define ``celery_poll_interval``.

.. code-block:: python

   CELERY_TASK_MONITOR_POLL_INTERVAL = 5000  # default

``CELERY_TASK_MONITOR_TRACE_PERMISSION``
===========================================

Nome completo (``app_label.codename``) da permissão que libera a
visualização do stacktrace completo de uma tarefa que falhou. Ver
:doc:`permissions`.

.. code-block:: python

   CELERY_TASK_MONITOR_TRACE_PERMISSION = "django_celery_task_monitor.view_task_trace"  # default

``CELERY_TASK_MONITOR_FRIENDLY_ERROR_MESSAGE``
==================================================

Mensagem exibida a usuários sem a permissão acima quando uma tarefa falha.

.. code-block:: python

   CELERY_TASK_MONITOR_FRIENDLY_ERROR_MESSAGE = "A tarefa falhou. Fale com o suporte."

``CELERY_TASK_MONITOR_LIST_PER_PAGE``
========================================

Número de itens por página no changelist do ``TaskLogAdmin``.

.. code-block:: python

   CELERY_TASK_MONITOR_LIST_PER_PAGE = 50  # default

Configuração do Celery no projeto host
=========================================

O plugin não configura o Celery — isso continua sendo responsabilidade do
seu projeto. Para o polling funcionar, o backend de resultados do Celery
precisa ser o ``django-db`` (fornecido por ``django-celery-results``):

.. code-block:: python

   CELERY_RESULT_BACKEND = "django-db"

Se você usar ``CELERY_TASK_ALWAYS_EAGER = True`` (por exemplo, em testes ou
para rodar sem worker/broker), lembre-se de também ativar
``CELERY_TASK_STORE_EAGER_RESULT = True`` — caso contrário, tarefas eager não
persistem o ``TaskResult`` e o polling nunca sai de ``PENDING``:

.. code-block:: python

   CELERY_TASK_ALWAYS_EAGER = True
   CELERY_TASK_STORE_EAGER_RESULT = True  # essencial para eager + monitor

Também ative ``CELERY_TASK_TRACK_STARTED = True``. Sem isso, o Celery nunca
registra o momento em que a execução começou (``TaskResult.date_started``
fica ``null``), e o painel ao vivo do change form (ver :doc:`usage`) fica
preso em "Tarefa enfileirada." mesmo com a tarefa já em execução:

.. code-block:: python

   CELERY_TASK_TRACK_STARTED = True

.. important::
   Em modo eager (``CELERY_TASK_ALWAYS_EAGER = True``), a tarefa roda de
   forma **síncrona**, dentro da própria requisição HTTP que a disparou —
   ela já terminou antes mesmo da página ser reenviada ao navegador. Ou
   seja, mesmo com ``CELERY_TASK_TRACK_STARTED`` ativado, os estados
   intermediários ("em processamento", progresso percentual) nunca chegam
   a ser vistos via polling: o painel salta direto de "Tarefa enfileirada."
   para o resultado final. Isso é esperado, não um bug — para ver a
   progressão completa ao vivo, use um broker de verdade (Redis/RabbitMQ) e
   rode um worker Celery separado (sem ``CELERY_TASK_ALWAYS_EAGER``).
