# Sandbox: testando o plugin em Django 5.2 e Django 6.1

Esta pasta existe só para testes manuais do `django_celery_task_monitor`
contra duas versões diferentes do Django, lado a lado, **sem duplicar a app
de teste**: `sandbox_app/` é compartilhada pelos dois projetos.

```
sandbox/
├── sandbox_app/        # app Django compartilhada (modelo, admin, task Celery)
├── django52/            # projeto Django 5.2, próprio venv
└── django61/            # projeto Django 6.1, próprio venv
```

Cada projeto (`django52/`, `django61/`) tem seu próprio `manage.py`,
`config/settings.py` e `requirements.txt` — só a versão do Django instalada
no respectivo venv muda. `config/settings.py` insere `sandbox/` no
`sys.path` para que `sandbox_app` seja importável como app de primeiro
nível em ambos, e cada projeto tem seu próprio `db.sqlite3` (bancos
independentes, mesmo schema).

## Por que não reaproveitar `example/`?

`example/` (na raiz do repo) é o projeto de exemplo "oficial", documentado
no README/docs, fixado numa única versão do Django (a mais recente
suportada). `sandbox/` é para você comparar comportamento entre versões
lado a lado ao investigar um bug ou validar compatibilidade antes de uma
release — os dois podem conviver.

## Rodando o Django 5.2

```bash
cd sandbox/django52
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8052
```

## Rodando o Django 6.1

Em outro terminal (venv separado, não misture com o do 5.2):

```bash
cd sandbox/django61
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8061
```

Com os dois rodando ao mesmo tempo (`:8052` e `:8061`), dá pra abrir os dois
admins lado a lado e comparar o comportamento do
`CeleryTaskMonitorMixin`/badge/polling entre as duas versões do Django.

## O que testar

1. Criar um "Item de sandbox" no admin (`/admin/sandbox_app/sandboxitem/add/`).
2. Abrir o item e clicar em "Processar (assíncrono)".
3. Confirmar que a coluna de status no changelist muda de "Pendente" para
   "Concluída" sozinha, via polling, sem recarregar a página.
4. Repetir a mesma sequência no outro projeto e comparar.

Ambos os projetos já rodam com `CELERY_TASK_ALWAYS_EAGER = True` e
`CELERY_TASK_STORE_EAGER_RESULT = True`, então tarefas executam de forma
síncrona e ainda assim persistem `TaskResult` — não é preciso worker nem
broker de verdade (ver a nota correspondente em `docs/configuration.rst`).

## Alterando o plugin

Os dois projetos instalam `django_celery_task_monitor` em modo editável
(`-e ../..` no `requirements.txt`), então qualquer mudança no código do
plugin (na raiz do repo) aparece imediatamente nos dois sandboxes, sem
reinstalar — só reiniciar o `runserver` se a mudança não for hot-reloadada
automaticamente.
