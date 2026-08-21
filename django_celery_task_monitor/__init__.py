"""django-celery-task-monitor: monitoramento de tarefas Celery no Django Admin.

Fornece um modelo genérico (``TaskLog``) para vincular tarefas Celery a
qualquer instância de modelo Django, um mixin de ``ModelAdmin`` para exibir
o status da tarefa no changelist com polling via REST, e um conjunto de
utilitários JavaScript/template para renderizar o progresso em tempo real.
"""

__version__ = "0.1.0"
