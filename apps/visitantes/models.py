from django.db import models


class Visitante(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_visitante',
    )
    entidad = models.CharField(max_length=200, blank=True, default='')
    cargo = models.CharField(max_length=150, blank=True, default='')

    def __str__(self):
        return str(self.persona)
