from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = [
        'username', 'email', 'nombres', 'apellidos',
        'rol_sistema', 'activo', 'is_staff', 'is_superuser', 'ultimo_acceso',
    ]
    list_filter = [
        'rol_sistema', 'activo', 'is_staff', 'is_superuser',
        'date_joined', 'ultimo_acceso',
    ]
    search_fields = [
        'username', 'email', 'nombres', 'apellidos',
    ]
    filter_horizontal = ['groups', 'user_permissions']
    readonly_fields = [
        'date_joined', 'last_login', 'ultimo_acceso',
    ]
    ordering = ['apellidos', 'nombres']

    fieldsets = (
        (None, {
            'fields': ('username', 'password'),
        }),
        ('Información Personal', {
            'fields': ('nombres', 'apellidos', 'email', 'rol_sistema', 'activo'),
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas', {
            'fields': ('last_login', 'date_joined', 'ultimo_acceso'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'nombres', 'apellidos',
                'rol_sistema', 'password1', 'password2',
                'activo', 'is_staff', 'is_superuser',
            ),
        }),
    )
