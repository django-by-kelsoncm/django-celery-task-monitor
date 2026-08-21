"""Modelo de sandbox, compartilhado pelos projetos django52/ e django61/.

Vive fora de qualquer um dos dois projetos para que a mesma app (e os
mesmos dados/migrations) possa ser testada com Django 5.2 e Django 6.1 sem
duplicar código — só a versão do Django instalada no venv de cada projeto
muda.
"""

from django.db import models


class SandboxItem(models.Model):
    """Item fictício processado de forma assíncrona, para exercitar o plugin."""

    nome = models.CharField(max_length=255)
    processado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "item de sandbox"
        verbose_name_plural = "itens de sandbox"

    def __str__(self) -> str:
        return self.nome
