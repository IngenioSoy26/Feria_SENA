from django.contrib import admin
from .models import InstitucionEducativa


@admin.register(InstitucionEducativa)
class InstitucionEducativaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'municipio', 'secretaria_educacion', 'activo',
    ]
    list_filter = ['activo', 'municipio']
    search_fields = ['nombre', 'codigo', 'municipio', 'secretaria_educacion']
    autocomplete_fields = []
    readonly_fields = []
    list_per_page = 30
    ordering = ['nombre']
    list_display_links = ['codigo', 'nombre']
    list_editable = ['activo']
    prepopulated_fields = {}
    save_on_top = True
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'municipio', 'secretaria_educacion'),
        }),
        ('Estado', {
            'fields': ('activo',),
        }),
    )
