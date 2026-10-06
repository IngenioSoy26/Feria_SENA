from django.contrib import admin
from .models import Proyecto, Aprendiz, Ficha


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'institucion', 'programa', 'grado', 'municipio',
        '_instructor', 'activo',
    ]
    list_filter = [
        'activo', 'institucion', 'programa', 'grado', 'municipio',
        'instructor_lider',
    ]
    search_fields = [
        'numero', 'institucion__nombre', 'programa__nombre',
        'grado', 'municipio', 'instructor_lider__persona__nombres',
        'instructor_lider__persona__apellidos',
        'telefono_instructor', 'correo_instructor',
    ]
    autocomplete_fields = [
        'institucion', 'programa', 'instructor_lider',
    ]
    readonly_fields = ['fecha_creacion']
    list_per_page = 30
    ordering = ['numero']
    list_display_links = ['numero']
    list_editable = ['activo']
    save_on_top = True

    def _instructor(self, obj):
        if obj.instructor_lider:
            return obj.instructor_lider.persona.nombre_completo
        return '—'
    _instructor.short_description = 'Instructor Líder'
    _instructor.admin_order_field = 'instructor_lider__persona__apellidos'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'institucion', 'programa',
            'instructor_lider', 'instructor_lider__persona',
        )

    fieldsets = (
        ('Identificación', {
            'fields': ('numero', 'activo'),
        }),
        ('Vinculaciones', {
            'fields': ('institucion', 'programa', 'grado', 'municipio'),
        }),
        ('Instructor Líder', {
            'fields': ('instructor_lider', 'telefono_instructor', 'correo_instructor'),
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin'),
        }),
        ('Auditoría (solo lectura)', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',),
        }),
    )


class AprendizInline(admin.TabularInline):
    model = Aprendiz
    extra = 0
    fields = ['persona', 'grado']
    autocomplete_fields = ['persona']


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'evento', 'institucion',
        'programa', '_instructor', 'estado',
        '_num_aprendices', 'fecha_creacion',
    ]
    list_filter = [
        'estado', 'evento', 'institucion', 'programa',
        'instructor_responsable',
        ('fecha_creacion', admin.DateFieldListFilter),
    ]
    search_fields = [
        'codigo', 'nombre', 'descripcion',
        'institucion__nombre', 'programa__nombre', 'evento__nombre',
    ]
    autocomplete_fields = [
        'evento', 'institucion', 'programa', 'instructor_responsable',
    ]
    readonly_fields = ['fecha_creacion']
    list_per_page = 25
    ordering = ['-fecha_creacion']
    list_display_links = ['codigo', 'nombre']
    list_editable = ['estado']
    date_hierarchy = 'fecha_creacion'
    save_on_top = True
    inlines = [AprendizInline]

    def _instructor(self, obj):
        if obj.instructor_responsable:
            return obj.instructor_responsable.persona.nombre_completo
        return '—'
    _instructor.short_description = 'Instructor'
    _instructor.admin_order_field = 'instructor_responsable__persona__apellidos'

    def _num_aprendices(self, obj):
        return obj.aprendices.count()
    _num_aprendices.short_description = 'Aprendices'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'evento', 'institucion', 'programa',
            'instructor_responsable', 'instructor_responsable__persona',
        ).prefetch_related('aprendices')

    fieldsets = (
        ('Clasificación', {
            'fields': ('evento', 'codigo', 'estado'),
        }),
        ('Información Principal', {
            'fields': ('nombre', 'descripcion'),
        }),
        ('Vinculaciones', {
            'fields': ('institucion', 'programa', 'instructor_responsable'),
        }),
        ('Auditoría (solo lectura)', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',),
        }),
    )


@admin.register(Aprendiz)
class AprendizAdmin(admin.ModelAdmin):
    list_display = [
        '_identificacion', '_nombre_completo',
        'proyecto', 'grado',
    ]
    list_filter = [
        'grado', 'proyecto__evento', 'proyecto__programa',
    ]
    search_fields = [
        'persona__nombres', 'persona__apellidos',
        'persona__numero_identificacion', 'grado',
        'proyecto__codigo', 'proyecto__nombre',
    ]
    autocomplete_fields = ['persona', 'proyecto']
    readonly_fields = []
    list_per_page = 40
    list_display_links = ['_identificacion', '_nombre_completo']
    save_on_top = True

    def _identificacion(self, obj):
        return obj.persona.numero_identificacion
    _identificacion.short_description = 'Identificación'
    _identificacion.admin_order_field = 'persona__numero_identificacion'

    def _nombre_completo(self, obj):
        return obj.persona.nombre_completo
    _nombre_completo.short_description = 'Nombre Completo'
    _nombre_completo.admin_order_field = 'persona__apellidos'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'persona', 'persona__tipo_identificacion',
            'proyecto', 'proyecto__evento', 'proyecto__programa',
        )
