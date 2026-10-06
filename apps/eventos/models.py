from django.db import models

from apps.usuarios.models import Usuario


class TipoIdentificacion(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipo de Identificación'
        verbose_name_plural = 'Tipos de Identificación'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Evento(models.Model):
    ESTADOS = (
        ('BORRADOR', 'Borrador'),
        ('ACTIVO', 'Activo'),
        ('CERRADO', 'Cerrado'),
    )

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    lugar = models.CharField(max_length=200)
    municipio = models.CharField(max_length=100)
    regional = models.CharField(max_length=100, default='Guajira')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')
    activo = models.BooleanField(default=True, db_index=True)
    creado_por = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.nombre


class TipoServicio(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='tipos_servicio')
    nombre = models.CharField(max_length=60)
    orden = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'Tipo de Servicio'
        verbose_name_plural = 'Tipos de Servicio'
        constraints = [
            models.UniqueConstraint(fields=['evento', 'nombre'], name='uq_tiposervicio_evento_nombre'),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.evento.nombre})"
