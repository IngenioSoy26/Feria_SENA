from django.db import models


class EntregaServicio(models.Model):
    MEDIOS = (
        ('QR', 'QR'),
        ('MANUAL', 'Búsqueda Manual'),
    )

    evento = models.ForeignKey(
        'eventos.Evento',
        on_delete=models.CASCADE,
    )
    persona = models.ForeignKey(
        'personas.Persona',
        on_delete=models.CASCADE,
    )
    tipo_servicio = models.ForeignKey(
        'eventos.TipoServicio',
        on_delete=models.PROTECT,
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
                fields=['evento', 'persona', 'tipo_servicio'],
                name='uq_entrega_evento_persona_servicio',
            ),
        ]

    def __str__(self):
        return f'{self.evento} - {self.persona} - {self.tipo_servicio}'
