"""
Migración de datos: crea los roles integrados del sistema en la tabla usuarios_rol.
"""
from django.db import migrations


ROLES_INICIALES = [
    {
        'codigo': 'ADMINISTRADOR',
        'nombre': 'Administrador',
        'descripcion': 'Acceso completo al sistema',
        'icono': '🛡',
        'color': 'bg-rojo text-white',
        'es_sistema': True,
        'areas_permitidas': [
            'dashboard', 'eventos', 'usuarios', 'roles', 'instituciones',
            'programas', 'instructores', 'personas', 'invitados',
            'proyectos', 'escarapelas', 'asistencia', 'refrigerios',
            'certificados', 'reportes', 'auditoria', 'listados',
            'perfil', 'logout',
        ],
    },
    {
        'codigo': 'GERENTE',
        'nombre': 'Gerente',
        'descripcion': 'Dashboard y listados (solo lectura)',
        'icono': '📊',
        'color': 'bg-purpura text-white',
        'es_sistema': True,
        'areas_permitidas': ['dashboard', 'listados', 'perfil', 'logout'],
    },
    {
        'codigo': 'OPERADOR_ASISTENCIA',
        'nombre': 'Operador de Asistencia',
        'descripcion': 'Registro de asistencia por QR',
        'icono': '✅',
        'color': 'bg-verde-claro text-white',
        'es_sistema': True,
        'areas_permitidas': ['asistencia', 'perfil', 'logout'],
    },
    {
        'codigo': 'OPERADOR_REFRIGERIO',
        'nombre': 'Operador de Refrigerio',
        'descripcion': 'Control de refrigerios/almuerzos',
        'icono': '🍱',
        'color': 'bg-naranja text-white',
        'es_sistema': True,
        'areas_permitidas': ['refrigerios', 'perfil', 'logout'],
    },
    {
        'codigo': 'OPERADOR_CERTIFICADO',
        'nombre': 'Operador de Certificado',
        'descripcion': 'Entrega de certificados',
        'icono': '📜',
        'color': 'bg-azul-o text-white',
        'es_sistema': True,
        'areas_permitidas': ['certificados', 'perfil', 'logout'],
    },
    {
        'codigo': 'REGISTRO',
        'nombre': 'Registro',
        'descripcion': 'Registro de proyectos, fichas y participantes',
        'icono': '📝',
        'color': 'bg-verde text-white',
        'es_sistema': True,
        'areas_permitidas': [
            'dashboard', 'eventos', 'personas', 'invitados',
            'proyectos', 'escarapelas', 'asistencia',
            'refrigerios', 'certificados', 'listados',
            'perfil', 'logout',
        ],
    },
    {
        'codigo': 'CONSULTA',
        'nombre': 'Consulta',
        'descripcion': 'Solo lectura de dashboard y listados',
        'icono': '🔍',
        'color': 'bg-gris text-white',
        'es_sistema': True,
        'areas_permitidas': ['dashboard', 'listados', 'perfil', 'logout'],
    },
]


def crear_roles(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    for datos in ROLES_INICIALES:
        Rol.objects.update_or_create(
            codigo=datos['codigo'],
            defaults={
                'nombre': datos['nombre'],
                'descripcion': datos['descripcion'],
                'icono': datos['icono'],
                'color': datos['color'],
                'es_sistema': datos['es_sistema'],
                'activo': True,
                'areas_permitidas': datos['areas_permitidas'],
            },
        )


def eliminar_roles(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    for datos in ROLES_INICIALES:
        Rol.objects.filter(codigo=datos['codigo'], es_sistema=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_rol'),
    ]

    operations = [
        migrations.RunPython(crear_roles, eliminar_roles),
    ]
