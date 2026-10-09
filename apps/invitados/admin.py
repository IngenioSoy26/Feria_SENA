from django.contrib import admin
from .models import Invitado


def _tiene_campo_activo():
    try:
        Invitado._meta.get_field('activo')
        return True
    except Exception:
        return False


_LIST_DISPLAY_BASE = [
    '_identificacion', '_nombre_completo',
    'entidad', 'cargo', '_correo',
]
_LIST_FILTER_BASE = ['entidad']
_LIST_EDITABLE_BASE = []
_FIELDSETS_BASE = (
    ('Persona', {
        'fields': ('persona',),
    }),
    ('Perfil Invitado', {
        'fields': ('entidad', 'cargo'),
    }),
)

if _tiene_campo_activo():
    list_display = _LIST_DISPLAY_BASE + ['activo']
    list_filter = ['activo'] + _LIST_FILTER_BASE
    list_editable = ['activo']
    fieldsets = (
        ('Persona', {'fields': ('persona',)}),
        ('Perfil Invitado', {'fields': ('entidad', 'cargo', 'activo')}),
    )
else:
    list_display = _LIST_DISPLAY_BASE
    list_filter = _LIST_FILTER_BASE
    list_editable = _LIST_EDITABLE_BASE
    fieldsets = _FIELDSETS_BASE


@admin.register(Invitado)
class InvitadoAdmin(admin.ModelAdmin):
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

    def get_list_display(self, request):
        base = super().get_list_display(request)
        if _tiene_campo_activo():
            return list(_LIST_DISPLAY_BASE) + ['activo']
        return list(_LIST_DISPLAY_BASE)

    def get_list_filter(self, request):
        base = super().get_list_filter(request)
        if _tiene_campo_activo():
            return ['activo'] + list(_LIST_FILTER_BASE)
        return list(_LIST_FILTER_BASE)

    def get_list_editable(self, request):
        if _tiene_campo_activo():
            return ['activo']
        return []

    def get_fieldsets(self, request, obj=None):
        if _tiene_campo_activo():
            return (
                ('Persona', {'fields': ('persona',)}),
                ('Perfil Invitado', {'fields': ('entidad', 'cargo', 'activo')}),
            )
        return _FIELDSETS_BASE

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
