from django.contrib import admin
from .models import Invitado


@admin.register(Invitado)
class InvitadoAdmin(admin.ModelAdmin):
    list_display = [
        '_identificacion', '_nombre_completo',
        'entidad', 'cargo', '_correo',
    ]
    list_filter = [
        'entidad',
    ]
    search_fields = [
        'persona__nombres', 'persona__apellidos',
        'persona__numero_identificacion', 'entidad', 'cargo',
        'persona__correo',
    ]
    autocomplete_fields = ['persona']
    readonly_fields = []
    list_per_page = 30
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

    def _correo(self, obj):
        return obj.persona.correo or '—'
    _correo.short_description = 'Correo'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('persona', 'persona__tipo_identificacion')

    fieldsets = (
        ('Persona', {
            'fields': ('persona',),
        }),
        ('Perfil Invitado', {
            'fields': ('entidad', 'cargo'),
        }),
    )
