import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Ficha(models.Model):
    numero = models.CharField(max_length=7, unique=True, db_index=True)
    institucion = models.ForeignKey(
        'instituciones.InstitucionEducativa',
        on_delete=models.PROTECT,
        related_name='fichas',
    )
    programa = models.ForeignKey(
        'programas.ProgramaTecnico',
        on_delete=models.PROTECT,
        related_name='fichas',
    )
    grado = models.CharField(max_length=10, blank=True, default='11')
    municipio = models.CharField(max_length=100, blank=True)
    instructor_lider = models.ForeignKey(
        'instructores.Instructor',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='fichas_dirigidas',
    )
    telefono_instructor = models.CharField(max_length=30, null=True, blank=True)
    correo_instructor = models.EmailField(max_length=180, null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ficha'
        verbose_name_plural = 'Fichas'
        ordering = ['numero']
        constraints = [
            models.UniqueConstraint(
                fields=['numero'],
                name='uq_ficha_numero',
            ),
        ]

    def __str__(self):
        return f'{self.numero} - {self.programa.nombre if self.programa_id else "Sin programa"}'

    def save(self, *args, **kwargs):
        if self.numero:
            self.numero = re.sub(r'\D', '', str(self.numero))[:7].zfill(7)
        super().save(*args, **kwargs)


class Proyecto(models.Model):
    ESTADOS = (
        ('INSCRITO', 'Inscrito'),
        ('APROBADO', 'Aprobado'),
        ('RETIRADO', 'Retirado'),
    )

    evento = models.ForeignKey(
        'eventos.Evento',
        on_delete=models.PROTECT,
        related_name='proyectos',
    )
    ficha = models.ForeignKey(
        Ficha,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='proyectos',
    )
    codigo = models.CharField(max_length=40, db_index=True)
    nombre = models.CharField(max_length=250)
    descripcion = models.TextField(blank=True)
    institucion = models.ForeignKey(
        'instituciones.InstitucionEducativa',
        on_delete=models.PROTECT,
        related_name='proyectos',
    )
    programa = models.ForeignKey(
        'programas.ProgramaTecnico',
        on_delete=models.PROTECT,
        related_name='proyectos',
    )
    instructor_responsable = models.ForeignKey(
        'instructores.Instructor',
        null=True,
        on_delete=models.SET_NULL,
        related_name='proyectos_dirigidos',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='INSCRITO',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['evento', 'codigo'],
                name='uq_proyecto_evento_codigo',
            ),
        ]

    def save(self, *args, **kwargs):
        self.nombre = (self.nombre or '').strip().upper() or self.nombre or ''
        if self.ficha_id and not self.codigo:
            # 1 proyecto por ficha -> 3160423, 2do+ -> 3160423-P2, 3160423-P3, etc.
            from django.db.models import Max
            ficha_num = str(self.ficha.numero)
            count_same_ficha = (
                Proyecto.objects
                .filter(ficha_id=self.ficha_id, evento_id=self.evento_id)
                .exclude(pk=self.pk)
                .count()
            )
            if count_same_ficha == 0:
                self.codigo = ficha_num
            else:
                self.codigo = f'{ficha_num}-P{count_same_ficha + 1}'
        if self.ficha_id:
            if not self.institucion_id:
                self.institucion = self.ficha.institucion
            if not self.programa_id:
                self.programa = self.ficha.programa
            if not self.instructor_responsable_id and self.ficha.instructor_lider_id:
                self.instructor_responsable = self.ficha.instructor_lider
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class Aprendiz(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_aprendiz',
    )
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.PROTECT,
        related_name='aprendices',
    )
    grado = models.CharField(max_length=10, default='11')
    entidad = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Entidad / I.E. / Colegio',
        help_text='Normalmente la institución del Proyecto (se rellena automáticamente).',
    )
    cargo = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        default='Aprendiz',
        verbose_name='Cargo / Rol',
    )

    class Meta:
        ordering = ['persona__apellidos', 'persona__nombres']

    def clean(self):
        super().clean()
        if self.persona_id and self.proyecto_id:
            qs = Aprendiz.objects.select_related('persona', 'proyecto').exclude(pk=self.pk)
            # Bloqueo 1: Misma PERSONA PK (OneToOne ya lo impide, doble check)
            ya_tiene = qs.filter(persona_id=self.persona_id).first()
            if not ya_tiene and self.persona.numero_identificacion:
                # Bloqueo 2: Mismo NÚMERO DE DOCUMENTO aunque sea con TIPO DE DOCUMENTO diferente
                # (ej: TI vs CC pero mismo número = misma persona)
                num = re.sub(r'\D', '', self.persona.numero_identificacion or '')
                if num:
                    otra_persona = qs.filter(
                        persona__numero_identificacion__regex=rf'^0*{num}0*$'
                    ).first()
                    if otra_persona:
                        ya_tiene = otra_persona
            if ya_tiene:
                nombre_proy = getattr(getattr(ya_tiene, 'proyecto', None), 'nombre', '') or ''
                codigo_proy = getattr(getattr(ya_tiene, 'proyecto', None), 'codigo', '') or ''
                ficha_num = ''
                if ya_tiene.proyecto and ya_tiene.proyecto.ficha_id:
                    ficha_num = f' · Ficha #{ya_tiene.proyecto.ficha.numero}'
                raise ValidationError({
                    'persona': (
                        f'❌ El aprendiz "{ya_tiene.persona.nombre_completo}" '
                        f'({ya_tiene.persona.tipo_identificacion.codigo} {ya_tiene.persona.numero_identificacion}) '
                        f'YA SE ENCUENTRA INSCRITO EN OTRO PROYECTO: '
                        f'"{nombre_proy}" (Código {codigo_proy}{ficha_num}). '
                        f'❕ CADA APRENDIZ SÓLO PUEDE PERTENECER A 1 (UN) PROYECTO. '
                        f'Si necesitas cambiarlo, elimina el aprendiz del proyecto original primero.'
                    )
                })

    def __str__(self):
        return str(self.persona)
