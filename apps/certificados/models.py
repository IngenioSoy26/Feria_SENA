import uuid

from django.db import models


class Certificado(models.Model):
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
    codigo_unico = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )
    token_verificacion = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    fecha_hora_entrega = models.DateTimeField(auto_now_add=True)
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
                name='uq_certificado_evento_persona',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo_unico:
            self.codigo_unico = (
                f'SENA-{self.evento_id}-{self.persona_id}-'
                f'{uuid.uuid4().hex[:8].upper()}'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo_unico
