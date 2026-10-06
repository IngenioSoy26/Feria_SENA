from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden


class RoleRequiredMixin(AccessMixin):
    roles_requeridos = None
    raise_exception = False
    permission_denied_message = '403 - No tiene rol autorizado para esta acción.'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.roles_requeridos:
            if not (request.user.is_superuser or request.user.groups.filter(
                name__in=self.roles_requeridos
            ).exists()):
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
