from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.Model):
    """Rol de sistema con permisos (áreas) configurables desde la app.

    Los roles del sistema (es_sistema=True) no se pueden eliminar.
    El código es el valor que se guarda en Usuario.rol_sistema.
    """

    codigo = models.CharField(max_length=40, unique=True, db_index=True,
                              help_text='Identificador único del rol (se guarda en el usuario)')
    nombre = models.CharField(max_length=80, help_text='Nombre visible del rol')
    descripcion = models.CharField(max_length=200, blank=True, default='')
    areas_permitidas = models.JSONField(
        default=list, blank=True,
        help_text='Lista de códigos de área a los que el rol tiene acceso',
    )
    icono = models.CharField(max_length=8, blank=True, default='', help_text='Emoji opcional')
    color = models.CharField(max_length=40, blank=True, default='bg-verde text-white',
                             help_text='Clase CSS de color para la insignia')
    es_sistema = models.BooleanField(default=False,
                                     help_text='Roles integrados: no se pueden eliminar')
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['es_sistema', 'nombre']
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'

    @property
    def areas(self) -> set:
        return set(self.areas_permitidas or [])

    def tiene_area(self, area: str) -> bool:
        return area in self.areas

    @property
    def areas_con_nombres(self):
        """Devuelve lista de (codigo, nombre) para las áreas permitidas."""
        from apps.usuarios.authorization import TODAS_LAS_AREAS
        nombres = dict(TODAS_LAS_AREAS)
        return [(a, nombres.get(a, a)) for a in (self.areas_permitidas or [])]


class Usuario(AbstractUser):
    ROLES_SISTEMA = (
        ('ADMINISTRADOR', 'Administrador'),
        ('REGISTRO', 'Registro'),
        ('GERENTE', 'Gerente'),
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
