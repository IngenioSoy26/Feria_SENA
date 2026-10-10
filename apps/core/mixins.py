from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib import messages

from apps.usuarios.authorization import (
    usuario_puede_acceder,
    AREA_DASHBOARD, AREA_ASISTENCIA, AREA_REFRIGERIOS, AREA_CERTIFICADOS,
)


class RoleRequiredMixin(AccessMixin):
    """
    V40 · Mixin que usa la MATRIZ DE ACCESO apps.usuarios.authorization.

      · Recibe `roles_requeridos` (legacy para compatibilidad con Dashboard)
      · PERO también usa las CONSTANTES DE ÁREA AREA_X del módulo authorization,
        que mapean a MATRIZ_ACCESOS por rol.

    Si permiso denegado:
      - Si no está autenticado → login redirect (igual que AccessMixin).
      - Sí autenticado pero sin permiso → redirect a su área permitida:
        · Admin/Registro/Gerente/Consulta → /dashboard/
        · OP_ASISTENCIA  → /asistencia/
        · OP_REFRIGERIO  → /refrigerios/
        · OP_CERTIFICADO → /certificados/
        · Como último recurso /accounts/profile/
      + mensaje error contacta al admin.
    """
    roles_requeridos = None
    areas_requeridas = None  # Lista de AREA_X de authorization
    raise_exception = False
    permission_denied_message = (
        'No tienes permiso para acceder a esta página. Contacta al Administrador.'
    )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if getattr(request.user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)

        permitido = False

        # 1) Validar por AREAS REQUERIDAS (usar MATRIZ autorización V40)
        areas = self.areas_requeridas or []
        if areas:
            permitido = usuario_puede_acceder(request, list(areas))

        # 2) Fallback legacy: roles_requeridos (strings de nombre de rol)
        if not permitido and self.roles_requeridos:
            try:
                rol_user = str(getattr(request.user, 'rol_sistema', '') or '').strip().upper()
                if rol_user and rol_user in {str(r).upper() for r in set(self.roles_requeridos)}:
                    permitido = True
            except Exception:
                pass
            if not permitido:
                try:
                    if request.user.groups.filter(name__in=list(self.roles_requeridos)).exists():
                        permitido = True
                except Exception:
                    pass

        if permitido:
            return super().dispatch(request, *args, **kwargs)

        # Permiso denegado:
        if self.raise_exception:
            return HttpResponseForbidden(self.permission_denied_message)
        try:
            messages.error(request, self.permission_denied_message)
        except Exception:
            pass
        # Redirige a su página inicial según rol
        if usuario_puede_acceder(request, AREA_DASHBOARD):
            return HttpResponseRedirect('/dashboard/')
        if usuario_puede_acceder(request, AREA_ASISTENCIA):
            return HttpResponseRedirect('/asistencia/')
        if usuario_puede_acceder(request, AREA_REFRIGERIOS):
            return HttpResponseRedirect('/refrigerios/')
        if usuario_puede_acceder(request, AREA_CERTIFICADOS):
            return HttpResponseRedirect('/certificados/')
        return HttpResponseRedirect('/accounts/profile/')


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

