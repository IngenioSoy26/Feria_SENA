from django.db import models


class ProgramaTecnico(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Programa Técnico'
        verbose_name_plural = 'Programas Técnicos'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
