# Contribuindo com django-celery-task-monitor

Obrigado por considerar contribuir! Este documento resume como configurar o
ambiente, os padrões de código esperados e como submeter mudanças.

## Configurando o ambiente

```bash
git clone https://github.com/django-by-kelsoncm/django-celery-task-monitor.git
cd django-celery-task-monitor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Isso instala o plugin em modo editável junto com Django, Celery,
`django-celery-results`, `pytest`, `black`, `flake8`, `mypy` e demais
ferramentas de desenvolvimento (ver `[project.optional-dependencies].dev` em
`pyproject.toml`).

## Rodando os testes

```bash
pytest
```

A suíte usa `pytest-django` com `tests/settings.py`, reaproveitando o app
`example_app` (pasta `example/`) como modelo alvo do `GenericForeignKey` de
`TaskLog` — não crie um segundo modelo de teste, adicione aos testes já
existentes em `tests/`.

## Rodando o projeto de exemplo

```bash
cd example
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

O exemplo roda com `CELERY_TASK_ALWAYS_EAGER = True` e
`CELERY_TASK_STORE_EAGER_RESULT = True`, então tarefas rodam de forma
síncrona e ainda assim persistem `TaskResult`, sem precisar de worker/broker
de verdade.

## Padrões de código

- **Formatação:** `black` (line length 100). Rode `black .` antes de commitar.
- **Lint:** `flake8` (`.flake8` na raiz).
- **Tipos:** o código é tipado; rode `mypy django_celery_task_monitor` antes
  de submeter. Novo código público deve ter type hints.
- **Docstrings:** toda função/método/classe pública deve ter uma docstring
  explicando o propósito (não apenas repetir a assinatura). Comentários
  inline só quando o *porquê* não é óbvio pelo código.
- **i18n:** todo texto voltado ao usuário usa `gettext`/`gettext_lazy`. Após
  adicionar ou mudar uma string, regenere as traduções:

  ```bash
  cd django_celery_task_monitor
  django-admin makemessages -l pt_BR -l en --no-location --no-obsolete
  # edite os .po gerados preenchendo os msgstr que faltam
  django-admin compilemessages
  ```

## Compatibilidade e breaking changes

O plugin busca manter compatibilidade com Django 4.2+, Celery 5.x e Python
3.10+. Mudanças que quebram a API pública (`TaskLog`, `CeleryTaskMonitorMixin`,
template tags, endpoints REST, nomes de settings) devem:

1. Ser discutidas em uma issue antes de implementadas, quando possível.
2. Manter um caminho de migração (deprecar antes de remover) sempre que
   viável.
3. Ser documentadas no changelog da release.

## Enviando uma mudança

1. Crie um fork e uma branch descritiva (`feature/...`, `fix/...`).
2. Escreva testes cobrindo a mudança — `pytest` precisa passar.
3. Rode `black`, `flake8` e `mypy` antes de abrir o PR.
4. Descreva no PR o quê e o porquê da mudança (não apenas o "como").
5. O CI (GitHub Actions) roda testes contra a matriz de Python/Django
   suportada; PRs só são mesclados com o CI verde.

## Reportando bugs

Abra uma issue com: versão do plugin, versão do Django/Celery/Python, passos
para reproduzir e o comportamento esperado vs. observado. Stacktraces
completos ajudam bastante.
