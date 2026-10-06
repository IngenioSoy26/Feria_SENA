from django.db import models


class Instructor(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_instructor',
    )
    programas = models.ManyToManyField(
        'programas.ProgramaTecnico',
        blank=True,
        related_name='instructores',
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return str(self.persona)
