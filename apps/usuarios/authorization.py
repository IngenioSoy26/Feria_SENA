"""
AUTORIZACIÓN V40.0 · Control de Acceso estricto por rol_sistema.

MATRIZ DE ACCESO EXACTA según usuario:
┌──────────────────────────┬───────────────────────────────────────────────┐
│ ROL                      │ ACCESOS PERMITIDOS                             │
├──────────────────────────┼───────────────────────────────────────────────┤
│ ADMINISTRADOR (is_staff) │ TODO (completo, sin restricciones)            │
│ GERENTE                  │ Dashboard + Perfil (cambiar clave) + Logout    │
│ OPERADOR_ASISTENCIA      │ /asistencia/ (y sus endpoints) + Perfil + Log│
│ OPERADOR_REFRIGERIO      │ /refrigerios/ (y sus endpoints) + Perfil + Lo │
│ OPERADOR_CERTIFICADO     │ /certificados/ (y sus endpoints) + Perfil + Lo│
│ REGISTRO                 │ Dashboard + Eventos + Personas + Invitados + P │
│ CONSULTA                 │ Dashboard + Perfil + Logout                    │
│ Usuario sin rol          │ NADA (solo login/perfil/logout si activo)     │
└──────────────────────────┴───────────────────────────────────────────────┘

Exports:
  · usuario_puede_acceder(request, area) → True/False
  · RolRequeridoMixin
  · rol_requerido_v40(roles_permitidos_list) decorator
  · generar_items_menu_por_rol(request) → [dict_items_navbar] para template
  · es_url_publica_permitida(path) → True si es ruta pública kiosco operador
"""
from functools import wraps

from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator

from .models import Usuario


# ============================================================
# 1) LISTA DE ÁREAS/ACCIONES QUE COMPONEN EL SISTEMA
# ============================================================
AREA_DASHBOARD = 'dashboard'
AREA_EVENTOS = 'eventos'
AREA_USUARIOS = 'usuarios'
AREA_INSTITUCIONES = 'instituciones'
AREA_PROGRAMAS = 'programas'
AREA_INSTRUCTORES = 'instructores'
AREA_PERSONAS = 'personas'
AREA_INVITADOS = 'invitados'
AREA_PROYECTOS = 'proyectos'
AREA_ESCARAPELAS = 'escarapelas'
AREA_ASISTENCIA = 'asistencia'
AREA_REFRIGERIOS = 'refrigerios'
AREA_CERTIFICADOS = 'certificados'
AREA_REPORTES = 'reportes'
AREA_AUDITORIA = 'auditoria'
AREA_PERFIL = 'perfil'
AREA_LOGOUT = 'logout'
AREA_PUBLICA = 'publica'

# Links predeterminados por rol del menú
_URLS_AREA = {
    AREA_DASHBOARD: '/dashboard/',
    AREA_EVENTOS: '/eventos/',
    AREA_USUARIOS: '/usuarios/',
    AREA_INSTITUCIONES: '/instituciones/',
    AREA_PROGRAMAS: '/programas/',
    AREA_INSTRUCTORES: '/instructores/',
    AREA_PERSONAS: '/personas/',
    AREA_INVITADOS: '/invitados/',
    AREA_PROYECTOS: '/proyectos/',
    AREA_ESCARAPELAS: '/escarapelas/',
    AREA_ASISTENCIA: '/asistencia/',
    AREA_REFRIGERIOS: '/refrigerios/',
    AREA_CERTIFICADOS: '/certificados/',
    AREA_REPORTES: '/reportes/',
    AREA_AUDITORIA: '/auditoria/',
    AREA_PERFIL: '/accounts/profile/',
    AREA_LOGOUT: '/accounts/logout/',
}

# ============================================================
# 2) MATRIZ: para cada rol, la LISTA de areas permitidas
# ============================================================
_MATRIZ_ACCESOS = {
    'ADMINISTRADOR': {
        AREA_DASHBOARD, AREA_EVENTOS, AREA_USUARIOS, AREA_INSTITUCIONES,
        AREA_PROGRAMAS, AREA_INSTRUCTORES, AREA_PERSONAS, AREA_INVITADOS,
        AREA_PROYECTOS, AREA_ESCARAPELAS, AREA_ASISTENCIA, AREA_REFRIGERIOS,
        AREA_CERTIFICADOS, AREA_REPORTES, AREA_AUDITORIA, AREA_PERFIL, AREA_LOGOUT
    },
    'GERENTE': {AREA_DASHBOARD, AREA_PERFIL, AREA_LOGOUT},
    'OPERADOR_ASISTENCIA': {AREA_ASISTENCIA, AREA_PERFIL, AREA_LOGOUT},
    'OPERADOR_REFRIGERIO': {AREA_REFRIGERIOS, AREA_PERFIL, AREA_LOGOUT},
    'OPERADOR_CERTIFICADO': {AREA_CERTIFICADOS, AREA_PERFIL, AREA_LOGOUT},
    'REGISTRO': {
        AREA_DASHBOARD, AREA_EVENTOS, AREA_PERSONAS, AREA_INVITADOS,
        AREA_PROYECTOS, AREA_ESCARAPELAS, AREA_ASISTENCIA,
        AREA_REFRIGERIOS, AREA_CERTIFICADOS, AREA_PERFIL, AREA_LOGOUT,
    },
    'CONSULTA': {AREA_DASHBOARD, AREA_PERFIL, AREA_LOGOUT},
}

# Rutas públicas (NO requieren auth, NO muestran navbar admin)
RUTAS_PUBLICAS_PREFIX = (
    '/r/',                  # Registro público kiosco: /r/<TOKEN>/registro/...
    '/o/',                  # Operadores público: /o/<TOKEN>/asistencia/ etc.
    '/accounts/login/',     # login (público)
    '/accounts/password_reset/',
    '/static/',
    '/media/',
    '/gracias/',            # gracias registro
)


def es_url_publica_permitida(path: str) -> bool:
    """Devuelve True si la URL es de acceso público (kiosco, operador, login)."""
    p = (path or '').strip()
    if not p:
        return False
    if p == '/' or p.startswith('/accounts/login'):
        return True
    return any(p.startswith(pref) for pref in RUTAS_PUBLICAS_PREFIX)


def _rol_del_usuario(request) -> str:
    """Extrae rol_sistema (o equivalente superuser/groups). Normaliza UPPER."""
    try:
        u = request.user
    except Exception:
        return ''
    if not u or not getattr(u, 'is_authenticated', False):
        return ''
    if getattr(u, 'is_superuser', False):
        return 'ADMINISTRADOR'
    try:
        r = str(getattr(u, 'rol_sistema', '') or '').strip().upper()
        if r:
            return r
    except Exception:
        pass
    try:
        gname = str(getattr(getattr(u, 'groups', None), 'name', '') or '').strip().upper()
        if gname:
            return gname
    except Exception:
        pass
    try:
        if u.groups.exists():
            for g in u.groups.all().order_by('id')[:1]:
                return (str(getattr(g, 'name', '')) or '').strip().upper()
    except Exception:
        pass
    if getattr(u, 'is_staff', False):
        return 'ADMINISTRADOR'
    return ''


def usuario_puede_acceder(request, area) -> bool:
    """API principal. area puede ser un string AREA_X o una LISTA de areas permitidas."""
    try:
        if not request.user or not request.user.is_authenticated:
            return False
    except Exception:
        return False
    try:
        if request.user.is_superuser:
            return True
    except Exception:
        pass
    if isinstance(area, (list, tuple, set)):
        areas = set(a for a in area if a)
    else:
        areas = {area}
    if not areas:
        return False
    rol = _rol_del_usuario(request)
    if not rol:
        return False
    permitidas = _MATRIZ_ACCESOS.get(rol) or set()
    return any(a in permitidas for a in areas)


# ============================================================
# 3) MIXIN para Vistas Basadas en Clase
# ============================================================
class RolRequeridoMixin:
    """
    Mixin para CBV: requiere login y rol válido para al menos una de areas_requeridas.
    Ejemplo:
        class DashboardView(RolRequeridoMixin, TemplateView):
            areas_requeridas = [AREA_DASHBOARD]
            ...
    """
    areas_requeridas = None
    raise_exception = True
    redirect_unauthenticated = True

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            if self.redirect_unauthenticated:
                return HttpResponseRedirect(
                    reverse('login') + f"?next={request.path}"
                )
            return HttpResponseForbidden('Autenticación requerida.')
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        areas_ok = self.areas_requeridas
        if areas_ok is None:
            try:
                areas_ok = list(self.roles_requeridos or [])
            except Exception:
                areas_ok = []
        if not areas_ok:
            return super().dispatch(request, *args, **kwargs)
        if not usuario_puede_acceder(request, areas_ok):
            if self.raise_exception:
                try:
                    messages.error(
                        request,
                        'No tienes permiso para acceder a esta página. Contacta al Administrador.'
                    )
                except Exception:
                    pass
                return HttpResponseRedirect('/dashboard/')
            return HttpResponseForbidden('Permiso denegado.')
        return super().dispatch(request, *args, **kwargs)


# ============================================================
# 4) DECORADOR para function views
# ============================================================
def rol_requerido_v40(areas_permitidas, login_required=True):
    """
    Decorator para function views.
    Ejemplo:
      @rol_requerido_v40([AREA_ASISTENCIA])
      def mi_vista_operador(request):
          ...
    """
    if isinstance(areas_permitidas, str):
        areas_permitidas = [areas_permitidas]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if login_required and (not getattr(request, 'user', None) or not request.user.is_authenticated):
                return HttpResponseRedirect(
                    reverse('login') + f"?next={request.path}"
                )
            if getattr(getattr(request, 'user', None), 'is_superuser', False):
                return view_func(request, *args, **kwargs)
            if not usuario_puede_acceder(request, list(areas_permitidas or [])):
                try:
                    messages.error(
                        request,
                        'No tienes permiso para acceder a esta página. Contacta al Administrador.'
                    )
                except Exception:
                    pass
                if request.user and request.user.is_authenticated:
                    try:
                        if usuario_puede_acceder(request, AREA_DASHBOARD):
                            return HttpResponseRedirect('/dashboard/')
                        if usuario_puede_acceder(request, AREA_ASISTENCIA):
                            return HttpResponseRedirect('/asistencia/')
                        if usuario_puede_acceder(request, AREA_REFRIGERIOS):
                            return HttpResponseRedirect('/refrigerios/')
                        if usuario_puede_acceder(request, AREA_CERTIFICADOS):
                            return HttpResponseRedirect('/certificados/')
                    except Exception:
                        pass
                return HttpResponseRedirect('/accounts/profile/')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============================================================
# 5) CONTEXT PROCESSOR -> items_menu para el navbar
# ============================================================
def generar_items_menu_por_rol(request):
    """Devuelve lista de dicts: [{"area":..., "label":..., "href":..., "icono":...},...]"""
    items = []
    if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return items
    if es_url_publica_permitida(request.path):
        return items
    try:
        if request.user.is_superuser:
            rol = 'ADMINISTRADOR'
        else:
            rol = _rol_del_usuario(request)
    except Exception:
        rol = _rol_del_usuario(request)
    permitidas = _MATRIZ_ACCESOS.get(rol) or set()

    def agregar_si_permite(area, label, icono=None):
        if area in permitidas and _URLS_AREA.get(area):
            items.append({
                'area': area,
                'label': label,
                'href': _URLS_AREA[area],
                'icono': icono or ''
            })

    if rol == 'ADMINISTRADOR':
        agregar_si_permite(AREA_DASHBOARD, 'Dashboard', '📊')
        agregar_si_permite(AREA_EVENTOS, 'Eventos', '📅')
        agregar_si_permite(AREA_USUARIOS, 'Usuarios', '👥')
        agregar_si_permite(AREA_INSTITUCIONES, 'Instituciones', '🏫')
        agregar_si_permite(AREA_PROGRAMAS, 'Programas', '📚')
        agregar_si_permite(AREA_INSTRUCTORES, 'Instructores', '👨‍🏫')
        agregar_si_permite(AREA_PERSONAS, 'Participantes', '🙋')
        agregar_si_permite(AREA_INVITADOS, 'Invitados', '🎟️')
        agregar_si_permite(AREA_PROYECTOS, 'Proyectos', '🛠️')
        agregar_si_permite(AREA_ESCARAPELAS, 'Escarapelas', '🪪')
        agregar_si_permite(AREA_ASISTENCIA, 'Asistencia', '✅')
        agregar_si_permite(AREA_REFRIGERIOS, 'Refrigerios', '🍱')
        agregar_si_permite(AREA_CERTIFICADOS, 'Certificados', '📜')
        agregar_si_permite(AREA_REPORTES, 'Reportes', '📈')
        agregar_si_permite(AREA_AUDITORIA, 'Auditoría', '🔍')
    elif rol == 'GERENTE':
        agregar_si_permite(AREA_DASHBOARD, 'Dashboard', '📊')
    elif rol == 'OPERADOR_ASISTENCIA':
        agregar_si_permite(AREA_ASISTENCIA, 'Asistencia', '✅')
    elif rol == 'OPERADOR_REFRIGERIO':
        agregar_si_permite(AREA_REFRIGERIOS, 'Refrigerios', '🍱')
    elif rol == 'OPERADOR_CERTIFICADO':
        agregar_si_permite(AREA_CERTIFICADOS, 'Certificados', '📜')
    elif rol == 'REGISTRO':
        agregar_si_permite(AREA_DASHBOARD, 'Dashboard', '📊')
        agregar_si_permite(AREA_EVENTOS, 'Eventos', '📅')
        agregar_si_permite(AREA_PERSONAS, 'Participantes', '🙋')
        agregar_si_permite(AREA_INVITADOS, 'Invitados', '🎟️')
        agregar_si_permite(AREA_PROYECTOS, 'Proyectos', '🛠️')
        agregar_si_permite(AREA_ESCARAPELAS, 'Escarapelas', '🪪')
        agregar_si_permite(AREA_ASISTENCIA, 'Asistencia', '✅')
        agregar_si_permite(AREA_REFRIGERIOS, 'Refrigerios', '🍱')
        agregar_si_permite(AREA_CERTIFICADOS, 'Certificados', '📜')
    elif rol == 'CONSULTA':
        agregar_si_permite(AREA_DASHBOARD, 'Dashboard', '📊')
    return items
