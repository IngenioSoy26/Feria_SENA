from django.contrib import admin
from .models import ProgramaTecnico


@admin.register(ProgramaTecnico)
class ProgramaTecnicoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'activo', '_num_instructores', '_num_proyectos',
    ]
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    autocomplete_fields = []
    readonly_fields = []
    list_per_page = 30
    ordering = ['nombre']
    list_display_links = ['codigo', 'nombre']
    list_editable = ['activo']
    save_on_top = True

    def _num_instructores(self, obj):
        return obj.instructores.count()
    _num_instructores.short_description = 'Instructores'
    _num_instructores.admin_order_field = 'instructores__count'

    def _num_proyectos(self, obj):
        return obj.proyectos.count()
    _num_proyectos.short_description = 'Proyectos'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('instructores', 'proyectos')

    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre'),
        }),
        ('Estado', {
            'fields': ('activo',),
        }),
    )
