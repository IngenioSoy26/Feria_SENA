from django.db import models


class Invitado(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_invitado',
    )
    entidad = models.CharField(max_length=200)
    cargo = models.CharField(max_length=150)

    def __str__(self):
        return str(self.persona)
