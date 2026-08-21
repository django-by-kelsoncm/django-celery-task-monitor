#!/usr/bin/env python
"""Utilitário de linha de comando do Django para o projeto de exemplo."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Ative o virtualenv e rode "
            "`pip install -e '..[dev]'` a partir da pasta example/."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
