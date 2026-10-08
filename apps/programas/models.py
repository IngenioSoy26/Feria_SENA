from django.db import models


def _generar_codigo_programa():
    from django.db.models import Max
    ultimo = ProgramaTecnico.objects.aggregate(m=Max('id'))['m'] or 0
    return f'PR-{int(ultimo) + 1:04d}'


class ProgramaTecnico(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
        default=_generar_codigo_programa,
        verbose_name='Código Programa'
    )
    nombre = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Programa Técnico'
        verbose_name_plural = 'Programas Técnicos'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _generar_codigo_programa()
        self.codigo = (self.codigo or '').strip().upper()
        self.nombre = (self.nombre or '').strip().upper() or self.nombre or ''
        super().save(*args, **kwargs)
