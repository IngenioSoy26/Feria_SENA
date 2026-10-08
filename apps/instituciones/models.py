from django.db import models


def _generar_codigo_ie():
    from django.db.models import Max
    ultimo = InstitucionEducativa.objects.aggregate(m=Max('id'))['m'] or 0
    return f'IE-{int(ultimo) + 1:04d}'


def _generar_codigo_municipio():
    from django.db.models import Max
    ultimo = Municipio.objects.aggregate(m=Max('id'))['m'] or 0
    return f'M-{int(ultimo) + 1:04d}'


class Municipio(models.Model):
    codigo = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        default=_generar_codigo_municipio,
        verbose_name='Código Municipio',
    )
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    departamento = models.CharField(max_length=100, default='LA GUAJIRA', verbose_name='Departamento')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'
        ordering = ['departamento', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _generar_codigo_municipio()
        self.codigo = (self.codigo or '').strip().upper()
        self.nombre = (self.nombre or '').strip().upper() or self.nombre or ''
        self.departamento = (self.departamento or '').strip().upper() or self.departamento or ''
        super().save(*args, **kwargs)


class InstitucionEducativa(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
        default=_generar_codigo_ie,
        verbose_name='Código Único IE',
        help_text='Identificador único automático (IE-XXXX). Se genera al crear la institución.'
    )
    nombre = models.CharField(max_length=250, unique=True)
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='instituciones',
        verbose_name='Municipio'
    )
    secretaria_educacion = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Secretaría de Educación'
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name='Teléfono',
        help_text='Teléfono principal de la institución (opcional)'
    )
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
        ordering = ['municipio', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _generar_codigo_ie()
        self.nombre = (self.nombre or '').strip().upper() or self.nombre or ''
        if self.codigo:
            self.codigo = (self.codigo or '').strip().upper()
        if self.secretaria_educacion:
            self.secretaria_educacion = (self.secretaria_educacion or '').strip().upper()
        if self.nombre_rector:
            self.nombre_rector = (self.nombre_rector or '').strip().upper()
        if self.nombre_coordinador:
            self.nombre_coordinador = (self.nombre_coordinador or '').strip().upper()
        if self.telefono:
            self.telefono = ''.join(ch for ch in str(self.telefono or '') if ch.isdigit() or ch == '+') or None
        if self.telefono_rector:
            self.telefono_rector = ''.join(ch for ch in str(self.telefono_rector or '') if ch.isdigit() or ch == '+') or None
        if self.celular_coordinador:
            self.celular_coordinador = ''.join(ch for ch in str(self.celular_coordinador or '') if ch.isdigit() or ch == '+') or None
        super().save(*args, **kwargs)
