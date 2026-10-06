from django.db import models


def evento_activo(request):
    contexto = {'evento_activo': None}
    try:
        from apps.eventos.models import Evento
        evento = Evento.objects.filter(activo=True).order_by('-fecha_inicio').first()
        contexto['evento_activo'] = evento
    except Exception:
        pass
    return contexto


def menu_dinamico_por_rol(request):
    menu = []
    usuario = request.user

    if not usuario.is_authenticated:
        return {'menu_dinamico': menu}

    es_superadmin = usuario.is_superuser

    def _tiene_grupo(nombres):
        if es_superadmin:
            return True
        if hasattr(usuario, 'groups') and usuario.groups.exists():
            return usuario.groups.filter(name__in=nombres).exists()
        return False

    es_admin = _tiene_grupo(['Administrador', 'Administrador del Sistema'])
    es_coordinador = _tiene_grupo(['Coordinador', 'Coordinador de Centro'])
    es_instructor = _tiene_grupo(['Instructor'])
    es_aprendiz = _tiene_grupo(['Aprendiz'])
    es_invitado = _tiene_grupo(['Invitado'])
    es_operativo = _tiene_grupo(['Operativo', 'Personal de Apoyo'])
    es_auditor = _tiene_grupo(['Auditor'])

    menu.append({
        'nombre': 'Dashboard',
        'url': 'dashboard:index',
        'icono': 'dashboard',
        'mostrar': True,
    })

    menu.append({
        'nombre': 'Eventos',
        'url': 'eventos:listar',
        'icono': 'calendar',
        'mostrar': True,
    })

    menu.append({
        'nombre': 'Personas',
        'url': 'personas:listar',
        'icono': 'users',
        'mostrar': es_admin or es_coordinador or es_instructor,
    })

    menu.append({
        'nombre': 'Instituciones',
        'url': 'instituciones:listar',
        'icono': 'building',
        'mostrar': es_admin or es_coordinador,
    })

    menu.append({
        'nombre': 'Programas',
        'url': 'programas:listar',
        'icono': 'book',
        'mostrar': es_admin or es_coordinador or es_instructor,
    })

    menu.append({
        'nombre': 'Proyectos',
        'url': 'proyectos:listar',
        'icono': 'folder',
        'mostrar': True,
    })

    menu.append({
        'nombre': 'Instructores',
        'url': 'instructores:listar',
        'icono': 'chalkboard',
        'mostrar': es_admin or es_coordinador,
    })

    menu.append({
        'nombre': 'Invitados',
        'url': 'invitados:listar',
        'icono': 'user-tie',
        'mostrar': es_admin or es_coordinador or es_operativo,
    })

    menu.append({
        'nombre': 'Escarapelas',
        'url': 'escarapelas:listar',
        'icono': 'id-card',
        'mostrar': es_admin or es_coordinador or es_operativo,
    })

    menu.append({
        'nombre': 'Asistencia',
        'url': 'asistencia:listar',
        'icono': 'check-square',
        'mostrar': True,
    })

    menu.append({
        'nombre': 'Refrigerios',
        'url': 'refrigerios:listar',
        'icono': 'coffee',
        'mostrar': es_admin or es_coordinador or es_operativo,
    })

    menu.append({
        'nombre': 'Certificados',
        'url': 'certificados:listar',
        'icono': 'award',
        'mostrar': True,
    })

    menu.append({
        'nombre': 'Usuarios',
        'url': 'usuarios:listar',
        'icono': 'user-shield',
        'mostrar': es_admin,
    })

    menu.append({
        'nombre': 'Reportes',
        'url': 'reportes:index',
        'icono': 'chart-bar',
        'mostrar': es_admin or es_coordinador or es_auditor,
    })

    menu.append({
        'nombre': 'Auditoría',
        'url': 'auditoria:listar',
        'icono': 'history',
        'mostrar': es_admin or es_auditor,
    })

    menu = [item for item in menu if item['mostrar']]

    return {'menu_dinamico': menu}
