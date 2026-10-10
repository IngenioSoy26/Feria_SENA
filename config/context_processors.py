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
    """
    V40: Usa la MATRIZ DE ACCESO apps.usuarios.authorization.generar_items_menu_por_rol.
      - Admin = TODO.
      - Gerente = solo Dashboard.
      - Operadores = SOLO su página operativa (Asistencia / Refrigerios / Certificados).
      - Ruta pública (ej: /r/<tok>/registro/visitantes/, /o/<tok>/asistencia/) → [] items.
    """
    menu = []
    try:
        from apps.usuarios.authorization import (
            generar_items_menu_por_rol as _g,
            es_url_publica_permitida as _e,
        )
        if getattr(request, 'path', None) and _e(request.path):
            return {
                'menu_dinamico': [],
                'menu_v40': [],
                'es_ruta_publica_v40': True,
            }
        items_v40 = _g(request) or []
        for it in items_v40:
            menu.append({
                'nombre': it.get('label', ''),
                'url': None,
                'href': it.get('href'),
                'icono': it.get('icono', ''),
                'area': it.get('area'),
                'mostrar': True,
            })
        return {
            'menu_dinamico': menu,
            'menu_v40': items_v40,
            'es_ruta_publica_v40': False,
        }
    except Exception as ex:
        return {
            'menu_dinamico': menu,
            'menu_v40': [],
            'es_ruta_publica_v40': False,
            '_err_authz': str(ex),
        }

