from django.db import models


class Instructor(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_instructor',
    )
    entidad = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default='SENA',
        verbose_name='Entidad / Centro SENA',
    )
    cargo = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        default='Instructor',
        verbose_name='Cargo / Perfil',
    )
    programas = models.ManyToManyField(
        'programas.ProgramaTecnico',
        blank=True,
        related_name='instructores',
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return str(self.persona)
