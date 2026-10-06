from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROLES_SISTEMA = (
        ('ADMINISTRADOR', 'Administrador'),
        ('REGISTRO', 'Registro'),
        ('OPERADOR_ASISTENCIA', 'Operador de Asistencia'),
        ('OPERADOR_REFRIGERIO', 'Operador de Refrigerio'),
        ('OPERADOR_CERTIFICADO', 'Operador de Certificado'),
        ('CONSULTA', 'Consulta'),
    )

    email = models.EmailField(unique=True)
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    rol_sistema = models.CharField(max_length=30, choices=ROLES_SISTEMA, db_index=True)
    activo = models.BooleanField(default=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    REQUIRED_FIELDS = ['email', 'nombres', 'apellidos', 'rol_sistema']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    def __str__(self):
        return self.nombre_completo
