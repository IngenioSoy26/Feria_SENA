from django.contrib import admin
from .models import Persona


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_identificacion', 'nombre_completo_display',
        'tipo_identificacion', 'tipo_persona',
        'correo', 'telefono', 'activo', 'fecha_creacion',
    ]
    list_filter = [
        'tipo_persona', 'tipo_identificacion', 'activo',
        ('fecha_creacion', admin.DateFieldListFilter),
    ]
    search_fields = [
        'nombres', 'apellidos', 'numero_identificacion',
        'correo', 'correo_sena', 'correo_personal',
        'telefono', 'qr_token',
    ]
    autocomplete_fields = ['tipo_identificacion', 'creado_por']
    readonly_fields = ['fecha_creacion', 'qr_token']
    list_per_page = 30
    ordering = ['apellidos', 'nombres']
    list_display_links = ['numero_identificacion', 'nombre_completo_display']
    list_editable = ['activo', 'tipo_persona']
    date_hierarchy = 'fecha_creacion'
    save_on_top = True

    def nombre_completo_display(self, obj):
        return obj.nombre_completo
    nombre_completo_display.short_description = 'Nombre Completo'
    nombre_completo_display.admin_order_field = 'apellidos'

    fieldsets = (
        ('Identificación', {
            'fields': ('tipo_identificacion', 'numero_identificacion'),
        }),
        ('Datos Personales', {
            'fields': ('nombres', 'apellidos', 'correo', 'correo_sena', 'correo_personal', 'telefono', 'fecha_nacimiento'),
        }),
        ('Clasificación', {
            'fields': ('tipo_persona', 'activo', 'creado_por'),
        }),
        ('Token y Auditoría (solo lectura)', {
            'fields': ('qr_token', 'fecha_creacion'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
