from django.db import models


class AsistenciaEvento(models.Model):
    MEDIOS = (
        ('QR', 'QR'),
        ('MANUAL', 'Búsqueda Manual'),
    )

    evento = models.ForeignKey(
        'eventos.Evento',
        on_delete=models.CASCADE,
        related_name='asistencias',
    )
    persona = models.ForeignKey(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='asistencias',
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)
    operador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
    )
    medio = models.CharField(
        max_length=10,
        choices=MEDIOS,
        default='QR',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['evento', 'persona'],
                name='uq_asistencia_evento_persona',
            ),
        ]

    def __str__(self):
        return f'{self.evento} - {self.persona}'
