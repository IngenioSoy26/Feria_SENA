"""
AUTORIZACIÓN V41.0 · Control de Acceso por rol_sistema con roles DINÁMICOS en BD.

Los roles y sus áreas permitidas se almacenan en la tabla usuarios_rol.
La matriz _MATRIZ_ACCESOS se usa como respaldo (fallback) para los roles
integrados que aún no existen en BD o cuando la BD no está disponible.

Exports:
  · usuario_puede_acceder(request, area) → True/False
  · RolRequeridoMixin
  · rol_requerido_v40(roles_permitidos_list) decorator
  · generar_items_menu_por_rol(request) → [dict_items_navbar] para template
  · es_url_publica_permitida(path) → True si es ruta pública kiosco operador
  · obtener_matriz_accesos() → dict {codigo_rol: set(areas)}
  · recargar_matriz_roles() → invalida caché
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
AREA_ROLES = 'roles'
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
AREA_LISTADOS = 'listados'
AREA_PERFIL = 'perfil'
AREA_LOGOUT = 'logout'
AREA_PUBLICA = 'publica'

# Todas las áreas disponibles (para el formulario de roles)
TODAS_LAS_AREAS = [
    (AREA_DASHBOARD, '📊 Dashboard'),
    (AREA_EVENTOS, '📅 Eventos'),
    (AREA_USUARIOS, '👥 Usuarios'),
    (AREA_ROLES, '🔐 Roles y permisos'),
    (AREA_INSTITUCIONES, '🏫 Instituciones'),
    (AREA_PROGRAMAS, '📚 Programas'),
    (AREA_INSTRUCTORES, '👨‍🏫 Instructores'),
    (AREA_PERSONAS, '🙋 Participantes'),
    (AREA_INVITADOS, '🎟️ Invitados'),
    (AREA_PROYECTOS, '🛠️ Proyectos'),
    (AREA_ESCARAPELAS, '🪪 Escarapelas'),
    (AREA_ASISTENCIA, '✅ Asistencia'),
    (AREA_REFRIGERIOS, '🍱 Refrigerios'),
    (AREA_CERTIFICADOS, '📜 Certificados'),
    (AREA_REPORTES, '📈 Reportes'),
    (AREA_AUDITORIA, '🔍 Auditoría'),
    (AREA_LISTADOS, '📋 Listados'),
    (AREA_PERFIL, '👤 Perfil (cambiar contraseña)'),
    (AREA_LOGOUT, '🚪 Cerrar sesión'),
]

# Links predeterminados por rol del menú
_URLS_AREA = {
    AREA_DASHBOARD: '/dashboard/',
    AREA_EVENTOS: '/eventos/',
    AREA_USUARIOS: '/usuarios/',
    AREA_ROLES: '/roles/',
    AREA_INSTITUCIONES: '/instituciones/',
    AREA_PROGRAMAS: '/programas/',
    AREA_INSTRUCTORES: '/instructores/',
    AREA_PERSONAS: '/personas/',
    AREA_INVITADOS: '/invitados/',
    AREA_PROYECTOS: '/proyectos/',
    AREA_ESCARAPELAS: '/escarapelas/',
    AREA_ASISTENCIA: '/asistencia/ingreso/',
    AREA_REFRIGERIOS: '/refrigerios/ingreso/',
    AREA_CERTIFICADOS: '/certificados/entrega/',
    AREA_REPORTES: '/reportes/',
    AREA_AUDITORIA: '/auditoria/',
    AREA_LISTADOS: '/listados/proyectos/',
    AREA_PERFIL: '/accounts/profile/',
    AREA_LOGOUT: '/accounts/logout/',
}

# ============================================================
# 2) MATRIZ DE RESPALDO (fallback) para roles integrados
# ============================================================
_MATRIZ_ACCESOS = {
    'ADMINISTRADOR': {
        AREA_DASHBOARD, AREA_EVENTOS, AREA_USUARIOS, AREA_ROLES, AREA_INSTITUCIONES,
        AREA_PROGRAMAS, AREA_INSTRUCTORES, AREA_PERSONAS, AREA_INVITADOS,
        AREA_PROYECTOS, AREA_ESCARAPELAS, AREA_ASISTENCIA, AREA_REFRIGERIOS,
        AREA_CERTIFICADOS, AREA_REPORTES, AREA_AUDITORIA, AREA_LISTADOS,
        AREA_PERFIL, AREA_LOGOUT
    },
    'GERENTE': {AREA_DASHBOARD, AREA_LISTADOS, AREA_PERFIL, AREA_LOGOUT},
    'OPERADOR_ASISTENCIA': {AREA_ASISTENCIA, AREA_PERFIL, AREA_LOGOUT},
    'OPERADOR_REFRIGERIO': {AREA_REFRIGERIOS, AREA_PERFIL, AREA_LOGOUT},
    'OPERADOR_CERTIFICADO': {AREA_CERTIFICADOS, AREA_PERFIL, AREA_LOGOUT},
    'REGISTRO': {
        AREA_DASHBOARD, AREA_EVENTOS, AREA_PERSONAS, AREA_INVITADOS,
        AREA_PROYECTOS, AREA_ESCARAPELAS, AREA_ASISTENCIA,
        AREA_REFRIGERIOS, AREA_CERTIFICADOS, AREA_LISTADOS,
        AREA_PERFIL, AREA_LOGOUT,
    },
    'CONSULTA': {AREA_DASHBOARD, AREA_LISTADOS, AREA_PERFIL, AREA_LOGOUT},
}

# Caché en memoria de la matriz leída de BD
_cache_matriz = None
_cache_roles_meta = None  # {codigo: {'nombre':..., 'icono':..., 'color':...}}

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


# ============================================================
# 2.1) MATRIZ DINÁMICA desde BD (con fallback a _MATRIZ_ACCESOS)
# ============================================================
def recargar_matriz_roles():
    """Invalida la caché de roles/permisos. Llamar al crear/editar/eliminar roles."""
    global _cache_matriz, _cache_roles_meta
    _cache_matriz = None
    _cache_roles_meta = None


def obtener_matriz_accesos() -> dict:
    """Devuelve {codigo_rol: set(areas_permitidas)} leyendo de BD con caché.

    Para cada rol en BD se usan sus áreas_permitidas. Si un rol integrado
    no existe en BD, se usa el fallback _MATRIZ_ACCESOS.
    """
    global _cache_matriz, _cache_roles_meta
    if _cache_matriz is not None:
        return _cache_matriz
    matriz = {}
    meta = {}
    try:
        from .models import Rol
        for r in Rol.objects.filter(activo=True).only('codigo', 'nombre', 'icono', 'color', 'areas_permitidas'):
            matriz[r.codigo] = set(r.areas_permitidas or [])
            meta[r.codigo] = {'nombre': r.nombre, 'icono': r.icono or '', 'color': r.color or ''}
    except Exception:
        # Si la tabla no existe o hay error, usamos solo el fallback
        pass
    # Fallback: roles integrados que no están en BD
    for codigo, areas in _MATRIZ_ACCESOS.items():
        if codigo not in matriz:
            matriz[codigo] = set(areas)
    _cache_matriz = matriz
    _cache_roles_meta = meta
    return matriz


def obtener_meta_roles() -> dict:
    """Devuelve {codigo: {'nombre', 'icono', 'color'}} desde BD con caché."""
    if _cache_roles_meta is None:
        obtener_matriz_accesos()
    return _cache_roles_meta or {}


def obtener_nombre_rol(codigo: str) -> str:
    """Devuelve el nombre visible de un rol (de BD o fallback)."""
    meta = obtener_meta_roles()
    if codigo in meta:
        return meta[codigo].get('nombre') or codigo
    # Fallback a ROLES_SISTEMA del modelo
    for cod, nombre in getattr(Usuario, 'ROLES_SISTEMA', ()):
        if cod == codigo:
            return nombre
    return codigo


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
    matriz = obtener_matriz_accesos()
    permitidas = matriz.get(rol) or set()
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
                            return HttpResponseRedirect('/asistencia/ingreso/')
                        if usuario_puede_acceder(request, AREA_REFRIGERIOS):
                            return HttpResponseRedirect('/refrigerios/ingreso/')
                        if usuario_puede_acceder(request, AREA_CERTIFICADOS):
                            return HttpResponseRedirect('/certificados/entrega/')
                    except Exception:
                        pass
                return HttpResponseRedirect('/accounts/profile/')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============================================================
# 5) CONTEXT PROCESSOR -> items_menu para el navbar
# ============================================================
# Mapa de área -> (label, icono) para generar el menú automáticamente
_LABELS_AREA_MENU = {
    AREA_DASHBOARD: ('Dashboard', '📊'),
    AREA_EVENTOS: ('Eventos', '📅'),
    AREA_USUARIOS: ('Usuarios', '👥'),
    AREA_ROLES: ('Roles', '🔐'),
    AREA_INSTITUCIONES: ('Instituciones', '🏫'),
    AREA_PROGRAMAS: ('Programas', '📚'),
    AREA_INSTRUCTORES: ('Instructores', '👨‍🏫'),
    AREA_PERSONAS: ('Participantes', '🙋'),
    AREA_INVITADOS: ('Invitados', '🎟️'),
    AREA_PROYECTOS: ('Proyectos', '🛠️'),
    AREA_ESCARAPELAS: ('Escarapelas', '🪪'),
    AREA_ASISTENCIA: ('Asistencia', '✅'),
    AREA_REFRIGERIOS: ('Refrigerios', '🍱'),
    AREA_CERTIFICADOS: ('Certificados', '📜'),
    AREA_REPORTES: ('Reportes', '📈'),
    AREA_AUDITORIA: ('Auditoría', '🔍'),
    AREA_LISTADOS: ('Listados', '📋'),
}


def generar_items_menu_por_rol(request):
    """Devuelve lista de dicts: [{"area":..., "label":..., "href":..., "icono":...},...]

    Genera el menú automáticamente a partir de las áreas permitidas del rol
    en la BD (o el fallback _MATRIZ_ACCESOS).
    """
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
    matriz = obtener_matriz_accesos()
    permitidas = matriz.get(rol) or set()

    # Iteramos en el orden definido en TODAS_LAS_AREAS para mantener consistencia
    for area, label_completo in TODAS_LAS_AREAS:
        if area in (AREA_PERFIL, AREA_LOGOUT, AREA_PUBLICA):
            continue  # no van en el navbar principal
        if area in permitidas and _URLS_AREA.get(area):
            label, icono = _LABELS_AREA_MENU.get(area, (label_completo, ''))
            items.append({
                'area': area,
                'label': label,
                'href': _URLS_AREA[area],
                'icono': icono,
            })
    return items
