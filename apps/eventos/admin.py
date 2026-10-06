from django.contrib import admin
from .models import Evento, TipoIdentificacion, TipoServicio


class TipoServicioInline(admin.TabularInline):
    model = TipoServicio
    extra = 0
    fields = ['nombre', 'orden', 'activo']
    prepopulated_fields = {}


@admin.register(TipoIdentificacion)
class TipoIdentificacionAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    autocomplete_fields = []
    readonly_fields = []
    list_per_page = 30
    ordering = ['nombre']
    list_editable = ['activo']


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'fecha_inicio', 'fecha_fin', 'municipio',
        'regional', 'estado', 'activo', '_num_proyectos', 'fecha_creacion',
    ]
    list_filter = [
        'estado', 'activo', 'regional', 'municipio',
        ('fecha_creacion', admin.DateFieldListFilter),
        ('fecha_inicio', admin.DateFieldListFilter),
    ]
    search_fields = ['nombre', 'descripcion', 'lugar', 'municipio', 'regional']
    autocomplete_fields = ['creado_por']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    list_per_page = 20
    ordering = ['-fecha_inicio']
    list_display_links = ['nombre']
    list_editable = ['estado', 'activo']
    date_hierarchy = 'fecha_inicio'
    save_on_top = True
    inlines = [TipoServicioInline]

    def _num_proyectos(self, obj):
        return obj.proyectos.count()
    _num_proyectos.short_description = 'Proyectos'

    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'descripcion', 'creado_por'),
        }),
        ('Fechas y Lugar', {
            'fields': ('fecha_inicio', 'fecha_fin', 'lugar', 'municipio', 'regional'),
        }),
        ('Estado y Control', {
            'fields': ('estado', 'activo'),
        }),
        ('Auditoría (solo lectura)', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            if 'fecha_creacion' not in ro:
                ro.append('fecha_creacion')
            if 'fecha_modificacion' not in ro:
                ro.append('fecha_modificacion')
        return ro

    def save_model(self, request, obj, form, change):
        if not change and not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
