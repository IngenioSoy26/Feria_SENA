import time
from collections import defaultdict
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_login_failed, user_logged_out
from django.dispatch import receiver
from django.http import HttpResponseForbidden
from django.urls import resolve


class AuditoriaMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.ip_usuario = self._obtener_ip(request)
        request.user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        return None

    def process_response(self, request, response):
        try:
            if hasattr(request, 'user') and request.user.is_authenticated:
                resolver_match = getattr(request, 'resolver_match', None)
                if resolver_match:
                    view_name = resolver_match.view_name
                    url_name = resolver_match.url_name
                    namespace = resolver_match.namespace
                    metodo = request.method
                    status_code = response.status_code
                    ip = getattr(request, 'ip_usuario', None)
                    user_agent = getattr(request, 'user_agent', '')
                    if metodo in ('PUT', 'PATCH'):
                        accion = 'UPDATE'
                    elif metodo == 'DELETE':
                        accion = 'DELETE'
                    elif metodo == 'POST':
                        accion = 'CREATE'
                    else:
                        accion = 'LOGIN'
                    self._registrar_bitacora(
                        usuario=request.user,
                        accion=accion,
                        modulo=(namespace or 'core')[:50],
                        entidad=(url_name or view_name or '')[:100] or None,
                        id_entidad=None,
                        datos={
                            'url': request.path,
                            'metodo': metodo,
                            'view': view_name,
                            'namespace': namespace,
                            'status': status_code,
                        },
                        ip=ip,
                        user_agent=user_agent,
                    )
        except Exception:
            pass
        return response

    def _obtener_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _registrar_bitacora(self, usuario, accion, modulo, entidad=None, id_entidad=None, datos=None, ip=None, user_agent=''):
        try:
            from apps.auditoria.models import AuditLog
            AuditLog.objects.create(
                usuario=usuario,
                accion=accion[:20],
                modulo=modulo[:50],
                entidad=(entidad or '')[:100] or None,
                id_entidad=id_entidad,
                datos=datos,
                ip=ip,
                user_agent=user_agent,
            )
        except Exception:
            pass


class RateLimitMiddleware(MiddlewareMixin):
    LIMITE_PETICIONES = 120
    VENTANA_SEGUNDOS = 60
    LIMITE_AUTENTICADO = 300

    _historial = defaultdict(list)

    def process_request(self, request):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return None

        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None

        identificador = self._identificador(request)
        ahora = time.time()
        if hasattr(request, 'user') and request.user.is_authenticated:
            limite = self.LIMITE_AUTENTICADO
        else:
            limite = self.LIMITE_PETICIONES

        historial = RateLimitMiddleware._historial[identificador]
        historial[:] = [t for t in historial if ahora - t < self.VENTANA_SEGUNDOS]

        if len(historial) >= limite:
            return HttpResponseForbidden(
                'Demasiadas peticiones. Por favor intente de nuevo en unos segundos.'
            )

        historial.append(ahora)
        return None

    def _identificador(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f'user:{request.user.pk}'
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return f'ip:{ip}'


@receiver(user_logged_in)
def al_iniciar_sesion(sender, request, user, **kwargs):
    ip = getattr(request, 'ip_usuario', None) if request else None
    user_agent = getattr(request, 'user_agent', '') if request else ''
    try:
        from apps.auditoria.models import AuditLog
        AuditLog.objects.create(
            usuario=user,
            accion='LOGIN',
            modulo='autenticacion',
            entidad='login_exito',
            datos={'username': user.username},
            ip=ip,
            user_agent=user_agent,
        )
    except Exception:
        pass


@receiver(user_login_failed)
def al_fallar_sesion(sender, credentials, request=None, **kwargs):
    ip = None
    user_agent = ''
    if request:
        ip = getattr(request, 'ip_usuario', None)
        user_agent = getattr(request, 'user_agent', '')
    username_intentado = ''
    if isinstance(credentials, dict):
        username_intentado = str(credentials.get('username', ''))[:100]
    try:
        from apps.auditoria.models import AuditLog
        AuditLog.objects.create(
            usuario=None,
            accion='LOGIN',
            modulo='autenticacion',
            entidad='login_fallo',
            datos={'username_intentado': username_intentado},
            ip=ip,
            user_agent=user_agent,
        )
    except Exception:
        pass


@receiver(user_logged_out)
def al_cerrar_sesion(sender, request, user, **kwargs):
    ip = getattr(request, 'ip_usuario', None) if request else None
    user_agent = getattr(request, 'user_agent', '') if request else ''
    try:
        from apps.auditoria.models import AuditLog
        AuditLog.objects.create(
            usuario=user,
            accion='LOGOUT',
            modulo='autenticacion',
            entidad='logout',
            datos={'username': user.username if user else ''},
            ip=ip,
            user_agent=user_agent,
        )
    except Exception:
        pass
