from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROLES_SISTEMA = (
        ('ADMINISTRADOR', 'Administrador · acceso completo'),
        ('REGISTRO', 'Registro · proyectos y fichas'),
        ('GERENTE', 'Gerente · solo Dashboard y reportes'),
        ('OPERADOR_ASISTENCIA', 'Operador de Asistencia · QR'),
        ('OPERADOR_REFRIGERIO', 'Operador de Refrigerio · almuerzo'),
        ('OPERADOR_CERTIFICADO', 'Operador de Certificado · entrega'),
        ('CONSULTA', 'Consulta · solo lectura'),
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

    def save(self, *args, **kwargs):
        self.nombres = (self.nombres or '').strip().upper()
        self.apellidos = (self.apellidos or '').strip().upper()
        self.username = (self.username or '').strip().lower()
        self.email = (self.email or '').strip().lower()
        # Sincronizamos SIEMPRE campos nativos AbstractUser con nuestros campos custom
        self.first_name = self.nombres or ''
        self.last_name = self.apellidos or ''
        self.is_active = bool(self.activo)
        return super().save(*args, **kwargs)
