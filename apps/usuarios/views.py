from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.contrib import messages

from apps.auditoria.models import AuditLog
from apps.usuarios.authorization import usuario_puede_acceder, AREA_PERFIL, AREA_DASHBOARD, AREA_ASISTENCIA, AREA_REFRIGERIOS, AREA_CERTIFICADOS
from apps.usuarios.models import Usuario


def get_redirect_url_por_rol(user):
    if user.is_superuser:
        return reverse('simple:home')
    if not hasattr(user, 'rol_sistema') or not user.rol_sistema:
        return reverse('simple:home')
    rol = user.rol_sistema
    if rol in ('ADMINISTRADOR', 'REGISTRO', 'CONSULTA', 'GERENTE'):
        return reverse('simple:home')
    if rol == 'OPERADOR_ASISTENCIA':
        return reverse('simple:operador', args=['asistencia'])
    if rol == 'OPERADOR_REFRIGERIO':
        return reverse('simple:operador', args=['refrigerios'])
    if rol == 'OPERADOR_CERTIFICADO':
        return reverse('simple:operador', args=['certificados'])
    return reverse('simple:home')


class PerfilView(LoginRequiredMixin, View):
    """V40: Perfil accesible para TODOS los usuarios autenticados (lo requieren Gerente/Operadores)."""
    template_name = 'usuarios/perfil.html'

    def dispatch(self, request, *args, **kwargs):
        if not usuario_puede_acceder(request, AREA_PERFIL):
            try:
                messages.error(request, 'No tienes permiso para acceder a esta página.')
            except Exception:
                pass
            if usuario_puede_acceder(request, AREA_DASHBOARD):
                return redirect('/dashboard/')
            if usuario_puede_acceder(request, AREA_ASISTENCIA):
                return redirect('/asistencia/')
            if usuario_puede_acceder(request, AREA_REFRIGERIOS):
                return redirect('/refrigerios/')
            if usuario_puede_acceder(request, AREA_CERTIFICADOS):
                return redirect('/certificados/')
            return redirect('/accounts/logout/')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        usuario = request.user
        context = {
            'usuario': usuario,
            'rol_nombre': usuario.get_rol_sistema_display() if hasattr(usuario, 'get_rol_sistema_display') else '',
            'cambiar_clave_url': reverse('usuarios:cambiar_clave'),
        }
        return TemplateResponse(request, self.template_name, context)


class CambiarClaveView(LoginRequiredMixin, PasswordChangeView):
    """V40: Vista de cambio de contraseña disponible para todos los roles."""
    template_name = 'usuarios/cambiar_clave.html'
    success_url = reverse_lazy('usuarios:perfil')

    def dispatch(self, request, *args, **kwargs):
        if not usuario_puede_acceder(request, AREA_PERFIL):
            try:
                messages.error(request, 'No tienes permiso para acceder a esta página.')
            except Exception:
                pass
            return redirect('/accounts/profile/')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        try:
            messages.success(self.request, '✅ Contraseña actualizada exitosamente.')
        except Exception:
            pass
        return response


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return get_redirect_url_por_rol(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        user.ultimo_acceso = timezone.now()
        user.save(update_fields=['ultimo_acceso'])
        ip = None
        x_forwarded = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            ip = x_forwarded.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')[:255]
        AuditLog.objects.create(
            usuario=user,
            accion='LOGIN',
            modulo='usuarios',
            entidad='Usuario',
            id_entidad=user.id,
            datos={
                'username': user.username,
                'rol': getattr(user, 'rol_sistema', ''),
            },
            ip=ip,
            user_agent=user_agent,
        )
        return response

