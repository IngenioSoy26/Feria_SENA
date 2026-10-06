from functools import wraps

from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect

from apps.core.services import AuditoriaService


def role_required(roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'ok': False,
                        'codigo': 401,
                        'error': 'Login requerido.',
                    }, status=401)
                return redirect(f'/accounts/login/?next={request.path}')

            if not (request.user.is_superuser or request.user.groups.filter(
                name__in=roles
            ).exists()):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'ok': False,
                        'codigo': 403,
                        'error': 'Rol no autorizado.',
                    }, status=403)
                return HttpResponseForbidden('403 - Rol no autorizado.')

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def ajax_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'ok': False,
                'codigo': 401,
                'error': 'Sesión expirada o usuario no autenticado.',
            }, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped


def auditar(accion=None, modulo=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            nombre_clase = view_func.__qualname__
            nombre_accion = accion or view_func.__name__
            entidad_pre = None
            id_entidad_pre = None

            AuditoriaService.registrar(
                request=request,
                usuario=getattr(request, 'user', None),
                accion=f'INICIO: {nombre_accion}',
                modulo=modulo or nombre_clase,
                entidad=entidad_pre,
                id_entidad=id_entidad_pre,
                datos={
                    'method': getattr(request, 'method', None),
                    'path': getattr(request, 'path', None),
                    'kwargs': kwargs,
                },
            )

            resultado = view_func(request, *args, **kwargs)

            estado = getattr(resultado, 'status_code', None)
            AuditoriaService.registrar(
                request=request,
                usuario=getattr(request, 'user', None),
                accion=f'FIN: {nombre_accion}',
                modulo=modulo or nombre_clase,
                entidad=entidad_pre,
                id_entidad=id_entidad_pre,
                datos={
                    'status_code': estado,
                },
            )

            return resultado
        return _wrapped
    return decorator
