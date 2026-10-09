from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden


class RoleRequiredMixin(AccessMixin):
    roles_requeridos = None
    raise_exception = False
    permission_denied_message = '403 - No tiene rol autorizado para esta acción. Consulte al administrador.'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.roles_requeridos:
            roles = set(self.roles_requeridos)
            # 1) Superusuario siempre OK
            if getattr(request.user, 'is_superuser', False):
                return super().dispatch(request, *args, **kwargs)
            # 2) Campo rol_sistema (Model Usuario) — forma NUEVA recomendada
            try:
                rol_user = str(getattr(request.user, 'rol_sistema', '') or '').strip().upper()
                if rol_user and rol_user in {str(r).upper() for r in roles}:
                    return super().dispatch(request, *args, **kwargs)
            except Exception:
                pass
            # 3) Grupo Django con nombre == rol — compatibilidad con usuarios creados en Admin Django
            try:
                if request.user.groups.filter(name__in=roles).exists():
                    return super().dispatch(request, *args, **kwargs)
            except Exception:
                pass
            return HttpResponseForbidden(self.permission_denied_message)

        return super().dispatch(request, *args, **kwargs)


class AjaxLoginRequiredMixin(AccessMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'ok': False,
                'codigo': 401,
                'error': 'Sesión expirada o usuario no autenticado.',
            }, status=401)
        return super().dispatch(request, *args, **kwargs)


class AjaxPermissionRequiredMixin(PermissionRequiredMixin):
    raise_exception = True

    def handle_no_permission(self):
        if self.raise_exception or self.request.headers.get(
            'X-Requested-With'
        ) == 'XMLHttpRequest':
            return JsonResponse({
                'ok': False,
                'codigo': 403,
                'error': 'Permiso insuficiente (HTTP 403). Consulte al administrador.',
            }, status=403)
        return super().handle_no_permission()
