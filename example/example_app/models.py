"""Modelo de exemplo usado para demonstrar o django_celery_task_monitor."""

from django.db import models


class Relatorio(models.Model):
    """Um "relatório" fictício que é processado de forma assíncrona."""

    nome = models.CharField(max_length=255)
    processado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "relatório"
        verbose_name_plural = "relatórios"

    def __str__(self) -> str:
        return self.nome
