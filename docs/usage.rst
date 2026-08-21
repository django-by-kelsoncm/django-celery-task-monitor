============
Uso Básico
============

O padrão de uso é: seu ``ModelAdmin`` herda de ``CeleryTaskMonitorMixin``,
adiciona ``task_status_column`` ao ``list_display``, e cria um ``TaskLog``
sempre que disparar uma tarefa a partir do admin.

Exemplo mínimo
================

.. code-block:: python

   from django.contrib import admin
   from django.contrib.contenttypes.models import ContentType
   from django.http import HttpResponseRedirect

   from django_celery_task_monitor.admin import CeleryTaskMonitorMixin
   from django_celery_task_monitor.models import TaskLog

   from .models import MeuModelo
   from .tasks import minha_task


   @admin.register(MeuModelo)
   class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
       list_display = ["nome", "campo1", "task_status_column"]

       def response_change(self, request, obj):
           if "_processar-async" in request.POST:
               task = minha_task.delay(obj.id)

               TaskLog.objects.create(
                   content_type=ContentType.objects.get_for_model(obj),
                   object_id=obj.id,
                   task_id=task.id,
                   task_name="minha_task",
                   started_by=request.user,
               )

               self.message_user(request, "Task iniciada!")
               return HttpResponseRedirect(request.path)

           return super().response_change(request, obj)

O que acontece automaticamente
=================================

1. A coluna ``task_status_column`` aparece no changelist, mostrando o
   :class:`~django_celery_task_monitor.models.TaskLog` mais recente
   vinculado a cada linha (ou ``—`` se nenhuma tarefa foi disparada ainda).
2. ``CeleryTaskMonitorMixin.get_urls()`` registra uma rota REST de polling
   específica para esta ``ModelAdmin``
   (``admin:<app_label>_<model_name>_celery_task_status``).
3. ``CeleryTaskMonitorMixin.media`` inclui ``task-poll.js`` (e o CSS
   opcional do badge) automaticamente — nenhum ``<script>`` manual é
   necessário.
4. ``task-poll.js`` se auto-inicializa em qualquer badge renderizado (ele
   procura elementos com o atributo ``data-poll-url``) assim que a página
   carrega, e para sozinho quando a tarefa atinge um estado final.

Adicionando o botão de disparo no formulário
===============================================

O exemplo acima reage a um campo ``_processar-async`` no ``POST``, mas o
Django admin não desenha esse botão por padrão. Sobrescreva o template
``change_form.html`` da sua ``ModelAdmin`` (veja
``example/example_app/templates/admin/example_app/relatorio/change_form.html``
no :doc:`projeto de exemplo <example-project>`):

.. code-block:: html+django

   {% extends "admin/change_form.html" %}

   {% block submit_buttons_bottom %}
     {{ block.super }}
     <div class="submit-row">
       <input type="submit" value="Processar (assíncrono)" name="_processar-async" class="default">
     </div>
   {% endblock %}

Mostrando o status ao vivo no change form
=============================================

A coluna do changelist já é ao vivo, mas o formulário de edição (a página
para onde ``response_change`` redireciona) não ganha nenhum indicador
sozinho — só a mensagem estática do Django (``self.message_user(...)``),
que nunca muda depois de renderizada. Para um painel que também sonda o
status e evolui em tempo real ("Tarefa enfileirada." → "Tarefa em
processamento há 12s." → "Tarefa finalizada com sucesso."), referencie
``{{ task_log_panel_html }}`` em algum lugar do seu ``change_form.html`` —
esse HTML já vem pronto no contexto, injetado automaticamente por
``CeleryTaskMonitorMixin.render_change_form()``:

.. code-block:: html+django

   {% extends "admin/change_form.html" %}

   {% block field_sets %}
     {{ task_log_panel_html }}
     {{ block.super }}
   {% endblock %}

   {% block submit_buttons_bottom %}
     {{ block.super }}
     <div class="submit-row">
       <input type="submit" value="Processar (assíncrono)" name="_processar-async" class="default">
     </div>
   {% endblock %}

``task_log_panel_html`` só existe no contexto do *change* view (não do
*add*, onde ainda não há objeto/``TaskLog`` nenhum) — em templates Django,
referenciar uma variável de contexto ausente simplesmente renderiza vazio,
então é seguro incluir o mesmo template em ambos. Detalhes de como a frase é
composta (e como customizá-la) estão em :doc:`advanced` e :doc:`javascript`.

Consultando todas as tarefas
===============================

``TaskLogAdmin`` (registrado automaticamente pelo plugin em
``/admin/django_celery_task_monitor/tasklog/``) lista todos os ``TaskLog``
de todos os modelos, com filtros por status, nome da tarefa e tipo de
conteúdo — útil como painel central de monitoramento, independente de qual
``ModelAdmin`` disparou a tarefa.
