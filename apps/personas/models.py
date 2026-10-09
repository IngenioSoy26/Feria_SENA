import uuid

from django.db import models

from apps.eventos.models import TipoIdentificacion
from apps.usuarios.models import Usuario


class Persona(models.Model):
    TIPOS = (
        ('APRENDIZ', 'Aprendiz'),
        ('INSTRUCTOR', 'Instructor'),
        ('INVITADO', 'Invitado'),
        ('ORGANIZADOR', 'Organizador'),
    )

    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT)
    numero_identificacion = models.CharField(max_length=30, db_index=True)
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    correo = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name='Fecha de nacimiento')
    correo_sena = models.EmailField(max_length=180, null=True, blank=True, verbose_name='Correo SENA')
    correo_personal = models.EmailField(max_length=180, null=True, blank=True, verbose_name='Correo personal')
    tipo_persona = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    entidad = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Entidad / Institución / Empresa',
        help_text='SENA · I.E. · Colegio · Alcaldía · Empresa · etc.',
    )
    cargo = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name='Cargo / Función / Rol en la Entidad',
        help_text='Aprendiz · Instructor · Coordinador · Rector · Invitado especial · etc.',
    )
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_identificacion', 'numero_identificacion'],
                name='uq_persona_tipo_numero_id'
            ),
        ]

    @property
    def nombre_completo(self):
        return f"{self.nombres or ''} {self.apellidos or ''}".strip()

    def get_full_name(self):
        return self.nombre_completo or f"Persona-{self.id}"

    def get_short_name(self):
        return (self.nombres or '').strip().split(' ')[0] or f"Persona-{self.id}"

    @property
    def entidad_canonica(self):
        _ent = None
        try:
            _ent = self.entidad
        except AttributeError:
            _ent = None
        if _ent:
            return _ent
        try:
            if self.tipo_persona == 'INVITADO':
                return (getattr(self.perfil_invitado, 'entidad', None) or '').strip().upper() or None
        except Exception:
            pass
        try:
            if self.tipo_persona == 'ORGANIZADOR':
                return (getattr(self.perfil_organizador, 'area_responsabilidad', None) or '').strip().upper() or None
        except Exception:
            pass
        try:
            if self.tipo_persona == 'APRENDIZ':
                perfil = getattr(self, 'perfil_aprendiz', None)
                if perfil and perfil.proyecto:
                    return (str(getattr(perfil.proyecto.institucion, 'nombre', '')) or '').upper() or None
        except Exception:
            pass
        if self.tipo_persona == 'INSTRUCTOR':
            return 'SENA'
        return None

    @property
    def cargo_canonico(self):
        _car = None
        try:
            _car = self.cargo
        except AttributeError:
            _car = None
        if _car:
            return _car
        try:
            if self.tipo_persona == 'INVITADO':
                _car = (getattr(self.perfil_invitado, 'cargo', None) or '').strip()
                return _car.title() if _car else None
        except Exception:
            pass
        try:
            if self.tipo_persona == 'ORGANIZADOR':
                _car = (getattr(self.perfil_organizador, 'cargo', None) or '').strip()
                return _car.title() if _car else None
        except Exception:
            pass
        if self.tipo_persona == 'APRENDIZ':
            return 'Aprendiz'
        if self.tipo_persona == 'INSTRUCTOR':
            return 'Instructor'
        return None

    def save(self, *args, **kwargs):
        self.nombres = (self.nombres or '').strip().upper() or self.nombres or ''
        self.apellidos = (self.apellidos or '').strip().upper() or self.apellidos or ''
        if self.correo:
            self.correo = (self.correo or '').strip().lower()
        if self.correo_sena:
            self.correo_sena = (self.correo_sena or '').strip().lower()
        if self.correo_personal:
            self.correo_personal = (self.correo_personal or '').strip().lower()
        try:
            if self.entidad is not None:
                _ent = (self.entidad or '').strip()
                self.entidad = _ent.upper() if _ent else None
        except AttributeError:
            pass
        try:
            if self.cargo is not None:
                _car = (self.cargo or '').strip()
                self.cargo = _car.title() if _car else None
        except AttributeError:
            pass
        if self._state.adding:
            while True:
                token = uuid.uuid4()
                if not Persona.objects.filter(qr_token=token).exists():
                    self.qr_token = token
                break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_completo
