from django.db import models


class InstitucionEducativa(models.Model):
    nombre = models.CharField(max_length=250, unique=True)
    municipio = models.CharField(max_length=100)
    secretaria_educacion = models.CharField(max_length=150, blank=True)
    codigo = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    zona = models.CharField(max_length=30, blank=True, null=True)
    sector = models.CharField(max_length=30, blank=True, null=True)
    caracter = models.CharField(max_length=50, blank=True, null=True, verbose_name='Carácter')
    especialidad = models.CharField(max_length=150, blank=True, null=True)
    direccion = models.CharField(max_length=250, blank=True, null=True, verbose_name='Dirección')
    correo_institucional = models.EmailField(max_length=180, blank=True, null=True)
    nombre_rector = models.CharField(max_length=180, blank=True, null=True)
    telefono_rector = models.CharField(max_length=30, blank=True, null=True)
    nombre_coordinador = models.CharField(max_length=180, blank=True, null=True)
    celular_coordinador = models.CharField(max_length=30, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Institución Educativa'
        verbose_name_plural = 'Instituciones Educativas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
