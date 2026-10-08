from django.db import models


class Organizador(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_organizador',
    )
    cargo = models.CharField(max_length=150, blank=True, null=True, verbose_name='Cargo / Función')
    area_responsabilidad = models.CharField(max_length=200, blank=True, null=True, verbose_name='Área / Punto de atención')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Organizador'
        verbose_name_plural = 'Organizadores'

    def __str__(self):
        extra = f' - {self.cargo}' if self.cargo else ''
        return f'{self.persona}{extra}'
