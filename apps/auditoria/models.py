from django.db import models


class AuditLog(models.Model):
    ACCIONES = (
        ('CREATE', 'Crear'),
        ('UPDATE', 'Modificar'),
        ('DELETE', 'Eliminar'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('IMPORT', 'Importación'),
        ('ASISTENCIA', 'Asistencia'),
        ('REFRIGERIO', 'Refrigerio'),
        ('CERTIFICADO', 'Certificado'),
    )

    usuario = models.ForeignKey(
        'usuarios.Usuario',
        null=True,
        on_delete=models.SET_NULL,
    )
    accion = models.CharField(
        max_length=20,
        choices=ACCIONES,
        db_index=True,
    )
    modulo = models.CharField(max_length=50, db_index=True)
    entidad = models.CharField(max_length=100, null=True)
    id_entidad = models.PositiveIntegerField(null=True)
    datos = models.JSONField(null=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'

    def __str__(self):
        return f'{self.accion} - {self.modulo} - {self.fecha_hora}'
