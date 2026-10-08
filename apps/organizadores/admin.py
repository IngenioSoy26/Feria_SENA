from django.contrib import admin
from .models import Organizador


@admin.register(Organizador)
class OrganizadorAdmin(admin.ModelAdmin):
    list_display = ('_nombre_completo', '_identificacion', 'cargo', 'area_responsabilidad', 'activo')
    list_filter = ('activo', 'area_responsabilidad')
    search_fields = (
        'persona__nombres', 'persona__apellidos',
        'persona__numero_identificacion', 'persona__correo',
        'cargo', 'area_responsabilidad',
    )
    autocomplete_fields = ['persona']

    def _identificacion(self, obj):
        if not obj.persona_id:
            return '-'
        ti = getattr(obj.persona, 'tipo_identificacion', None)
        abr = (getattr(ti, 'abreviatura', None) or getattr(ti, 'codigo', None) or '')
        return f'{abr} {obj.persona.numero_identificacion}'.strip()
    _identificacion.short_description = 'Identificación'
    _identificacion.admin_order_field = 'persona__numero_identificacion'

    def _nombre_completo(self, obj):
        return str(obj.persona) if obj.persona_id else '-'
    _nombre_completo.short_description = 'Nombre'
    _nombre_completo.admin_order_field = 'persona__apellidos'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('persona', 'persona__tipo_identificacion')
