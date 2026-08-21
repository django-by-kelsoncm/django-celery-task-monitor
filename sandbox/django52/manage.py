#!/usr/bin/env python
"""Utilitário de linha de comando do Django para o sandbox em Django 5.2."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Ative o virtualenv deste "
            "projeto (sandbox/django52/.venv) e rode "
            "`pip install -r requirements.txt` a partir desta pasta."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
