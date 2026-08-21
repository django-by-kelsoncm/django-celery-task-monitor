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

Cada projeto roda de forma **assíncrona de verdade**: um broker real
(`filesystem://`, do Kombu — fila baseada em arquivos, sem exigir Redis
instalado) e um worker Celery separado do processo web. É isso que permite
ver o ciclo completo ao vivo ("Tarefa enfileirada." → "Tarefa em
processamento há Xs." → "Processamento em Y%." → "Tarefa finalizada com
sucesso.") em vez de só o resultado final — em modo eager (o padrão de
`example/`, o exemplo "oficial" do README) a tarefa roda de forma síncrona
*dentro da própria requisição* que a disparou, e por mais que se aumente um
`time.sleep()` dentro dela, o navegador só recebe a resposta depois que ela
já terminou, então os estados intermediários nunca chegam a ser vistos via
polling.

Cada projeto precisa de **dois processos rodando ao mesmo tempo**: o
`runserver` (web) e um `celery worker` (processa a fila). `sandbox_app/tasks.py`
demora de propósito uns 10s (5 passos de 2s, publicando progresso a cada
passo) para dar tempo de ver o painel evoluir por vários polls antes de
terminar.

## Rodando o Django 5.2

Terminal 1 (web):

```bash
cd sandbox/django52
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8052
```

Terminal 2 (worker, mesmo venv):

```bash
cd sandbox/django52 && source .venv/bin/activate
celery -A config worker --loglevel=info --pool=solo
```

## Rodando o Django 6.1

Terminal 3 (web, venv separado — não misture com o do 5.2):

```bash
cd sandbox/django61
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8061
```

Terminal 4 (worker, mesmo venv):

```bash
cd sandbox/django61 && source .venv/bin/activate
celery -A config worker --loglevel=info --pool=solo
```

Com os quatro rodando ao mesmo tempo (`:8052` e `:8061`), dá pra abrir os
dois admins lado a lado e comparar o comportamento do
`CeleryTaskMonitorMixin`/badge/painel/polling entre as duas versões do
Django. `--pool=solo` evita a complexidade de multiprocessing do pool
padrão do Celery — ideal para um worker único de sandbox local.

## O que testar

1. Criar um "Item de sandbox" no admin (`/admin/sandbox_app/sandboxitem/add/`).
2. Abrir o item e clicar em "Processar (assíncrono)".
3. Acompanhar o painel ao vivo no próprio change form (e a coluna de status
   no changelist) evoluindo sozinho, via polling, sem recarregar a página:
   "Tarefa enfileirada." → "Tarefa em processamento há Xs. Processamento em
   Y%." (subindo a cada ~2s) → "Tarefa finalizada com sucesso.".
4. Repetir a mesma sequência no outro projeto e comparar.

Se o painel ficar preso em "Tarefa enfileirada." indefinidamente, confira se
o `celery worker` do terminal correspondente está mesmo rodando — sem ele a
task fica só enfileirada nos arquivos de `broker_queue/` e nunca executa.

## Alterando o plugin

Os dois projetos instalam `django_celery_task_monitor` em modo editável
(`-e ../..` no `requirements.txt`), então qualquer mudança no código do
plugin (na raiz do repo) aparece imediatamente nos dois sandboxes, sem
reinstalar — só reiniciar o `runserver` se a mudança não for hot-reloadada
automaticamente.
