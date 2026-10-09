from django.contrib import admin
from django.utils.html import format_html

from apps.asistencia.models import AsistenciaEvento
from apps.refrigerios.models import EntregaServicio
from apps.certificados.models import Certificado


def _badge_tipo_persona(tp):
    if tp == 'APRENDIZ':
        return format_html('<span class="badge" style="background:#16a34a;color:#fff;">APRENDIZ</span>')
    if tp == 'INSTRUCTOR':
        return format_html('<span class="badge" style="background:#0ea5e9;color:#fff;">INSTRUCTOR</span>')
    if tp == 'INVITADO':
        return format_html('<span class="badge" style="background:#a855f7;color:#fff;">INVITADO</span>')
    if tp == 'ORGANIZADOR':
        return format_html('<span class="badge" style="background:#f59e0b;color:#fff;">ORGANIZADOR</span>')
    return tp or '-'


def _operador_con_rol(u):
    if not u:
        return '-'
    name = f'{u.get_full_name() or u.username}'
    rol = str(getattr(u, 'rol_sistema', '') or '').strip()
    if rol:
        return f'{name} · [{rol}]'
    return name


@admin.register(AsistenciaEvento)
class AsistenciaEventoAdmin(admin.ModelAdmin):
    list_display = [
        'evento',
        'persona_numero',
        'persona_nombre',
        'tipo_persona',
        'fecha_hora',
        'operador_username',
        'medio',
    ]
    list_display_links = ['fecha_hora', 'persona_numero']
    list_filter = [
        'evento',
        'medio',
        'persona__tipo_persona',
        'operador__rol_sistema',
        ('fecha_hora', admin.DateFieldListFilter),
    ]
    search_fields = [
        'persona__numero_identificacion',
        'persona__nombres',
        'persona__apellidos',
        'persona__correo',
        'persona__qr_token',
        'operador__username',
        'operador__first_name',
        'operador__last_name',
    ]
    readonly_fields = ['fecha_hora']
    date_hierarchy = 'fecha_hora'
    list_per_page = 40
    save_on_top = True
    ordering = ['-fecha_hora']
    autocomplete_fields = ['evento', 'persona', 'operador']

    actions = ['eliminar_seleccionadas_asistencia']

    @admin.action(description='🗑️ Eliminar asistencias seleccionadas (reset)')
    def eliminar_seleccionadas_asistencia(self, request, queryset):
        n = queryset.count()
        queryset.delete()
        self.message_user(request, f'Se eliminaron {n} registro(s) de asistencia.')

    def persona_numero(self, obj):
        return getattr(obj.persona, 'numero_identificacion', '-')
    persona_numero.short_description = 'Documento'
    persona_numero.admin_order_field = 'persona__numero_identificacion'

    def persona_nombre(self, obj):
        return getattr(obj.persona, 'nombre_completo', '-')
    persona_nombre.short_description = 'Persona'
    persona_nombre.admin_order_field = 'persona__apellidos'

    def tipo_persona(self, obj):
        return _badge_tipo_persona(getattr(obj.persona, 'tipo_persona', '') or '')
    tipo_persona.short_description = 'Rol'
    tipo_persona.admin_order_field = 'persona__tipo_persona'

    def operador_username(self, obj):
        return _operador_con_rol(obj.operador)
    operador_username.short_description = '¿Quién lo marcó?'
    operador_username.admin_order_field = 'operador__username'

    fieldsets = (
        ('Evento y Persona', {
            'fields': ('evento', 'persona'),
        }),
        ('Marca / Auditoría', {
            'fields': ('fecha_hora', 'operador', 'medio'),
        }),
    )


@admin.register(EntregaServicio)
class EntregaServicioAdmin(admin.ModelAdmin):
    list_display = [
        'evento',
        'tipo_servicio',
        'persona_numero',
        'persona_nombre',
        'tipo_persona',
        'fecha_hora',
        'operador_username',
        'medio',
    ]
    list_display_links = ['fecha_hora', 'persona_numero']
    list_filter = [
        'evento',
        'tipo_servicio',
        'medio',
        'persona__tipo_persona',
        'operador__rol_sistema',
        ('fecha_hora', admin.DateFieldListFilter),
    ]
    search_fields = [
        'persona__numero_identificacion',
        'persona__nombres',
        'persona__apellidos',
        'persona__correo',
        'persona__qr_token',
        'operador__username',
        'operador__first_name',
        'operador__last_name',
        'tipo_servicio__nombre',
    ]
    readonly_fields = ['fecha_hora']
    date_hierarchy = 'fecha_hora'
    list_per_page = 40
    save_on_top = True
    ordering = ['-fecha_hora']
    autocomplete_fields = ['evento', 'persona', 'tipo_servicio', 'operador']

    actions = ['eliminar_seleccionadas_entrega']

    @admin.action(description='🗑️ Eliminar entregas seleccionadas (reset refrigerios)')
    def eliminar_seleccionadas_entrega(self, request, queryset):
        n = queryset.count()
        queryset.delete()
        self.message_user(request, f'Se eliminaron {n} entrega(s) de servicio (refrigerios).')

    def persona_numero(self, obj):
        return getattr(obj.persona, 'numero_identificacion', '-')
    persona_numero.short_description = 'Documento'
    persona_numero.admin_order_field = 'persona__numero_identificacion'

    def persona_nombre(self, obj):
        return getattr(obj.persona, 'nombre_completo', '-')
    persona_nombre.short_description = 'Persona'
    persona_nombre.admin_order_field = 'persona__apellidos'

    def tipo_persona(self, obj):
        return _badge_tipo_persona(getattr(obj.persona, 'tipo_persona', '') or '')
    tipo_persona.short_description = 'Rol'
    tipo_persona.admin_order_field = 'persona__tipo_persona'

    def operador_username(self, obj):
        return _operador_con_rol(obj.operador)
    operador_username.short_description = '¿Quién lo entregó?'
    operador_username.admin_order_field = 'operador__username'

    fieldsets = (
        ('Evento, Servicio y Persona', {
            'fields': ('evento', 'tipo_servicio', 'persona'),
        }),
        ('Entrega / Auditoría', {
            'fields': ('fecha_hora', 'operador', 'medio'),
        }),
    )


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = [
        'evento',
        'codigo_unico',
        'persona_numero',
        'persona_nombre',
        'tipo_persona',
        'fecha_hora_entrega',
        'operador_username',
        'medio',
    ]
    list_display_links = ['codigo_unico', 'fecha_hora_entrega']
    list_filter = [
        'evento',
        'medio',
        'persona__tipo_persona',
        'operador__rol_sistema',
        ('fecha_hora_entrega', admin.DateFieldListFilter),
    ]
    search_fields = [
        'codigo_unico',
        'persona__numero_identificacion',
        'persona__nombres',
        'persona__apellidos',
        'persona__correo',
        'persona__qr_token',
        'operador__username',
        'operador__first_name',
        'operador__last_name',
    ]
    readonly_fields = ['codigo_unico', 'token_verificacion', 'fecha_hora_entrega']
    date_hierarchy = 'fecha_hora_entrega'
    list_per_page = 40
    save_on_top = True
    ordering = ['-fecha_hora_entrega']
    autocomplete_fields = ['evento', 'persona', 'operador']

    actions = ['eliminar_seleccionados_certificados']

    @admin.action(description='🗑️ Eliminar certificados seleccionados (reset)')
    def eliminar_seleccionados_certificados(self, request, queryset):
        n = queryset.count()
        queryset.delete()
        self.message_user(request, f'Se eliminaron {n} certificado(s) entregado(s).')

    def persona_numero(self, obj):
        return getattr(obj.persona, 'numero_identificacion', '-')
    persona_numero.short_description = 'Documento'
    persona_numero.admin_order_field = 'persona__numero_identificacion'

    def persona_nombre(self, obj):
        return getattr(obj.persona, 'nombre_completo', '-')
    persona_nombre.short_description = 'Persona'
    persona_nombre.admin_order_field = 'persona__apellidos'

    def tipo_persona(self, obj):
        return _badge_tipo_persona(getattr(obj.persona, 'tipo_persona', '') or '')
    tipo_persona.short_description = 'Rol'
    tipo_persona.admin_order_field = 'persona__tipo_persona'

    def operador_username(self, obj):
        return _operador_con_rol(obj.operador)
    operador_username.short_description = '¿Quién lo entregó?'
    operador_username.admin_order_field = 'operador__username'

    fieldsets = (
        ('Evento y Persona', {
            'fields': ('evento', 'persona'),
        }),
        ('Códigos y auditoría (solo lectura)', {
            'fields': ('codigo_unico', 'token_verificacion', 'fecha_hora_entrega', 'operador', 'medio'),
            'classes': ('collapse',),
        }),
    )
