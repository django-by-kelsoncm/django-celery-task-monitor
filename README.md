# django-celery-task-monitor

Monitoramento de tarefas Celery no Django Admin, com polling via REST.

Vincule qualquer tarefa Celery disparada a partir do admin a qualquer modelo
do seu projeto (via `GenericForeignKey`), mostre uma coluna de status no
changelist que se atualiza sozinha (sem recarregar a página) e controle quem
pode ver o stacktrace completo quando uma tarefa falha.

## Funcionalidades

- **Modelo `TaskLog`** — vincula uma tarefa Celery a qualquer instância de
  modelo Django, sem acoplamento (`GenericForeignKey`).
- **Mixin `CeleryTaskMonitorMixin`** — adiciona uma coluna de status com
  polling automático a qualquer `ModelAdmin`.
- **Endpoint REST embutido** — cada `ModelAdmin` que usa o mixin ganha sua
  própria rota de polling, respeitando as permissões do admin.
- **JavaScript modular e auto-contido** (`task-poll.js`) — sem dependências
  externas, com limpeza automática de `setInterval` (sem memory leak) e
  suporte a múltiplas instâncias na mesma página.
- **`TaskLogAdmin`** — interface central para consultar todas as tarefas
  registradas, com filtros e paginação.
- **Controle de permissão granular** — usuários comuns veem uma mensagem de
  erro amigável; superusuários e usuários com a permissão `view_task_trace`
  veem o stacktrace completo.
- **Internacionalizado** — strings traduzidas para `pt-BR` e `en`.

## Instalação

```bash
pip install django-celery-task-monitor
```

O único pré-requisito é [`django-celery-results`](https://github.com/celery/django-celery-results),
que fornece o modelo `TaskResult` usado para consultar o resultado real das
tarefas.

## Configuração

Adicione as duas apps ao `settings.py` do seu projeto (`django_celery_results`
é uma dependência direta e precisa estar instalada também):

```python
INSTALLED_APPS = [
    # ...
    "django_celery_results",
    "django_celery_task_monitor",
]
```

Rode as migrações:

```bash
python manage.py migrate
```

Todas as configurações abaixo são opcionais — o plugin funciona com os
valores padrão:

```python
# Intervalo padrão (ms) do polling no changelist, usado quando o ModelAdmin
# não define `celery_poll_interval`. Default: 5000.
CELERY_TASK_MONITOR_POLL_INTERVAL = 5000

# Nome completo da permissão que libera o stacktrace. Default: já é este.
CELERY_TASK_MONITOR_TRACE_PERMISSION = "django_celery_task_monitor.view_task_trace"

# Mensagem exibida a quem não tem permissão de ver o stacktrace.
CELERY_TASK_MONITOR_FRIENDLY_ERROR_MESSAGE = "A tarefa falhou. Fale com o suporte."

# Itens por página no changelist do TaskLogAdmin. Default: 50.
CELERY_TASK_MONITOR_LIST_PER_PAGE = 50
```

A permissão `view_task_trace` é criada automaticamente pela migração do
plugin. Conceda-a a quem deve ver stacktraces completos (via admin de
`Usuários`/`Grupos`, ou por script/data migration no seu projeto).

Para o painel de status ao vivo do change form (ver "Uso básico" abaixo)
mostrar quando a tarefa realmente começou a rodar — e não ficar preso em
"Tarefa enfileirada." — ative também, na configuração do Celery do seu
projeto:

```python
CELERY_TASK_TRACK_STARTED = True
```

## Uso básico

```python
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
```

Isso é tudo: a coluna `task_status_column` aparece no changelist, mostra o
badge de status da tarefa mais recente vinculada a cada linha, e começa a
sondar o endpoint REST automaticamente assim que a página carrega — sem
nenhum JavaScript extra para escrever. Para o botão "Processar (assíncrono)"
aparecer no formulário, adicione um `submit_buttons_bottom` customizado (veja
`example/example_app/templates/admin/example_app/relatorio/change_form.html`
no projeto de exemplo).

**Importante:** o changelist ganha o badge automaticamente, mas o *change
form* (a página para onde `response_change` redireciona) não ganha nenhum
indicador ao vivo sozinho — só a mensagem estática de
`self.message_user(...)`, que nunca muda depois de renderizada. Se você
quiser um painel que também evolua em tempo real ali ("Tarefa enfileirada."
→ "Tarefa em processamento há 12s." → "Tarefa finalizada com sucesso."),
referencie `{{ task_log_panel_html }}` no seu `change_form.html` — o mixin
já injeta esse HTML pronto no contexto:

```html
{% extends "admin/change_form.html" %}

{% block field_sets %}
  {{ task_log_panel_html }}
  {{ block.super }}
{% endblock %}
```

## Uso avançado

### Customizar o intervalo de polling por ModelAdmin

```python
class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
    celery_poll_interval = 3000  # 3s, em vez do default global
```

### Customizar o nome da coluna/atributo

Use `celery_task_field` quando o nome padrão (`task_status_column`) colidir
com outro atributo já existente na sua `ModelAdmin`:

```python
class MeuModeloAdmin(CeleryTaskMonitorMixin, admin.ModelAdmin):
    celery_task_field = "status_da_tarefa"
    list_display = ["nome", "status_da_tarefa"]
```

### Usar o badge fora do admin

Template tags (`{% load task_monitor_tags %}`):

```html
{% load task_monitor_tags %}

{% task_status_badge my_task_log %}

{# ou, com URL/intervalo de polling customizados: #}
{% task_status_badge my_task_log poll_url=my_poll_url poll_interval=3000 %}

{# inclui o <script> do plugin com a inicialização já feita: #}
{% task_poll_script ".task-status-badge" %}
```

### Um endpoint REST único, fora do admin

`CeleryTaskMonitorMixin` já cria uma rota por `ModelAdmin`
(`admin:<app>_<model>_celery_task_status`). Se preferir um único endpoint
compartilhado fora do admin, use a view genérica:

```python
# urls.py
from django_celery_task_monitor.views import TaskStatusView

urlpatterns = [
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
]
```

### JavaScript: uso manual

`task-poll.js` se auto-inicializa em qualquer elemento com `data-poll-url`
(exatamente o que o template `task_status_badge.html` renderiza), então na
maioria dos casos você não precisa chamar nada manualmente. Para controle
fino (callbacks, seletor customizado):

```html
<script src="{% static 'django_celery_task_monitor/js/task-poll.js' %}"></script>
<script>
  TaskPoll.init(".task-badge", {
    pollInterval: 5000,
    endpoint: "/admin/task-status/",  // opcional se o elemento já tem data-poll-url
    onUpdate: function (data, el) { /* a cada resposta */ },
    onSuccess: function (data, el) { console.log("Task concluída!", data); },
    onError: function (data, el) { console.warn("Task falhou", data); },
  });
</script>
```

`TaskPoll.stop(el)` para um elemento específico, `TaskPoll.stopAll()` para
todos. Intervals são limpos automaticamente quando o elemento é removido do
DOM (via `MutationObserver`) e quando a tarefa atinge um estado final
(`SUCCESS`, `FAILURE` ou `REVOKED`).

Elementos com um `.task-status-panel__message` interno (renderizados por
`task_status_panel.html`) ganham a frase completa de status, recomposta a
cada poll e a cada segundo no cliente (relógio de "há X tempo"). Os textos
padrão (pt-BR) são customizáveis via `TaskPoll.configure({messages: {...}})`
ou por chamada via `options.messages` — veja `docs/javascript.rst`.

## Referência da API

### `django_celery_task_monitor.models.TaskLog`

| Campo/Método | Descrição |
| --- | --- |
| `content_type`, `object_id`, `content_object` | Vínculo genérico com qualquer modelo. |
| `task_id` | ID da tarefa Celery (único). |
| `task_name` | Nome da tarefa (informativo). |
| `status` | Status cacheado (`PENDING`, `STARTED`, `RETRY`, `PROGRESS`, `SUCCESS`, `FAILURE`, `REVOKED`, ou qualquer estado customizado). |
| `started_by` | Usuário que disparou a tarefa (opcional). |
| `update_status()` | Sincroniza `status` com o `TaskResult` mais recente. |
| `is_finished` | `True` se o status é terminal. |
| `get_progress()` | Dict de progresso (`{"percent": ...}`) publicado via `self.update_state(state=..., meta=...)`, ou `None`. |
| `get_status_message()` | Frase de status legível (ex.: `"Tarefa em processamento há 12s."`). |
| `get_error_details(user)` | `{"message": ..., "traceback": ...}`, respeitando a permissão de `user`. |
| `get_traceback()` | Stacktrace bruto, sem checar permissão (uso interno). |
| `as_status_payload(user)` | Payload JSON usado pelo endpoint de polling (inclui `message`, `started_at`, `progress`). |

### `django_celery_task_monitor.admin.CeleryTaskMonitorMixin`

| Atributo/Método | Descrição |
| --- | --- |
| `celery_poll_interval` | Intervalo de polling (ms) desta `ModelAdmin`. `None` usa o default global. |
| `celery_task_field` | Nome do atributo/coluna de status. Default: `"task_status_column"`. |
| `task_status_column(obj)` | Método de exibição padrão para `list_display`. |
| `get_celery_poll_interval()` | Intervalo efetivo (considerando o default global). |
| `get_urls()` | Registra a rota REST de polling (`admin:<app>_<model>_celery_task_status`). |
| `render_change_form(...)` | Injeta `task_log_panel_html` (painel ao vivo pronto) no contexto do change form. |

### `django_celery_task_monitor.admin.TaskLogAdmin`

Admin somente leitura (sem criação manual) registrado para `TaskLog`, com
filtros por `status`/`task_name`/`content_type`, busca por `task_id` e
`task_name`, e ocultação automática do campo de stacktrace completo para
quem não tem a permissão `view_task_trace`.

### Template tags (`{% load task_monitor_tags %}`)

| Tag | Descrição |
| --- | --- |
| `{% task_status_badge task_log %}` | Renderiza o badge de status (rótulo curto). |
| `{% task_status_panel task_log %}` | Renderiza o painel de status ao vivo (frase completa). |
| `{% task_poll_script selector %}` | `<script>` do plugin + inicialização do polling para `selector`. |
| `{% task_monitor_static_url %}` | URL estática de `task-poll.js`. |
| `{% task_monitor_static_css_url %}` | URL estática do CSS opcional do badge. |

### `django_celery_task_monitor.permissions.user_can_view_task_trace(user)`

Retorna `True` para superusuários e usuários com a permissão
`view_task_trace`; `False` para usuários anônimos/sem permissão.

## Exemplo completo

Veja [`example/`](example/) — um projeto Django mínimo com um `ModelAdmin`
usando `CeleryTaskMonitorMixin` exatamente como mostrado acima, incluindo o
botão "Processar (assíncrono)" no formulário de edição. Para rodar:

```bash
git clone https://github.com/django-by-kelsoncm/django-celery-task-monitor.git
cd django-celery-task-monitor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd example
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

O exemplo já roda com `CELERY_TASK_ALWAYS_EAGER = True` (sem precisar de
worker/broker) — veja `example/example_project/settings.py`.

## FAQ

**Como mostrar uma barra de progresso, em vez de só um badge de status?**

O plugin já lê progresso percentual nativamente: dentro da sua tarefa Celery
(com `bind=True`), chame `self.update_state(state="PROGRESS", meta={"percent": 42})`.
`TaskLog.get_progress()` decodifica isso, e tanto o payload JSON do endpoint
de polling (`progress.percent`) quanto a frase pronta do painel ao vivo
(`"Processamento em 42%."`) já refletem automaticamente — sem customização
necessária para o texto. Para uma barra visual em vez de só texto, use o
callback `onUpdate` de `TaskPoll.init()` para ler `data.progress.percent` a
cada poll e atualizar sua própria UI.

**Como integrar com Django-RQ (ou outra fila) em vez de Celery?**

O plugin depende de `django-celery-results` porque é isso que popula
`TaskResult.status`. Para outro backend de filas, você precisaria de um
adaptador equivalente que exponha algo parecido com `TaskResult` (com
`task_id`, `status`, `result`, `traceback`) — hoje isso está fora do escopo
do plugin. Uma alternativa mais simples: atualize `TaskLog.status`
diretamente a partir da sua própria fila (chamando `task_log.status = ...;
task_log.save()`), sem depender de `update_status()`/`TaskResult`.

**Como reprocessar uma tarefa que falhou?**

Isso é responsabilidade do seu `ModelAdmin` (o mesmo padrão do exemplo em
"Uso básico" acima), não do plugin — chame `minha_task.delay(...)` de novo e
crie um novo `TaskLog`. O `TaskLogAdmin` mostra o histórico completo de
tentativas, já que cada `TaskLog` é imutável quanto a `task_id`.

**Os badges antigos continuam fazendo polling para sempre?**

Não. O JavaScript para o `setInterval` automaticamente assim que a tarefa
atinge um status final (`SUCCESS`, `FAILURE` ou `REVOKED`) — veja
`TaskPoll` em [`task-poll.js`](django_celery_task_monitor/static/django_celery_task_monitor/js/task-poll.js).

## Compatibilidade

- Django 4.2+
- Celery 5.x
- Python 3.10+
- `django-celery-results` >= 2.5

## Desenvolvimento

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
black django_celery_task_monitor tests example
flake8
mypy django_celery_task_monitor
```

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para mais detalhes.

## Licença

[MIT](LICENSE)
