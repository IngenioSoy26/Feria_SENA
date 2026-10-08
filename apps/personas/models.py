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

    def save(self, *args, **kwargs):
        self.nombres = (self.nombres or '').strip().upper() or self.nombres or ''
        self.apellidos = (self.apellidos or '').strip().upper() or self.apellidos or ''
        if self.correo:
            self.correo = (self.correo or '').strip().lower()
        if self.correo_sena:
            self.correo_sena = (self.correo_sena or '').strip().lower()
        if self.correo_personal:
            self.correo_personal = (self.correo_personal or '').strip().lower()
        if self._state.adding:
            while True:
                token = uuid.uuid4()
                if not Persona.objects.filter(qr_token=token).exists():
                    self.qr_token = token
                break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_completo
