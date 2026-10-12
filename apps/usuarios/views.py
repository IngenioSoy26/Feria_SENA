from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.contrib import messages

from apps.auditoria.models import AuditLog
from apps.usuarios.authorization import (
    usuario_puede_acceder, AREA_PERFIL, AREA_DASHBOARD, AREA_ASISTENCIA,
    AREA_REFRIGERIOS, AREA_CERTIFICADOS, AREA_ROLES, TODAS_LAS_AREAS,
    recargar_matriz_roles, obtener_nombre_rol,
)
from apps.usuarios.models import Usuario, Rol
from apps.usuarios.forms import RolForm


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
                return redirect('/asistencia/ingreso/')
            if usuario_puede_acceder(request, AREA_REFRIGERIOS):
                return redirect('/refrigerios/ingreso/')
            if usuario_puede_acceder(request, AREA_CERTIFICADOS):
                return redirect('/certificados/entrega/')
            return redirect('/accounts/logout/')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        usuario = request.user
        context = {
            'usuario': usuario,
            'rol_nombre': obtener_nombre_rol(getattr(usuario, 'rol_sistema', '')),
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


# ============================================================
# GESTIÓN DE ROLES Y PERMISOS — solo ADMINISTRADOR
# ============================================================
def _requiere_admin_roles(request):
    """Devuelve True si el usuario puede gestionar roles."""
    if not request.user or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    return usuario_puede_acceder(request, AREA_ROLES)


class ListaRolesView(LoginRequiredMixin, View):
    template_name = 'usuarios/lista_roles.html'

    def dispatch(self, request, *args, **kwargs):
        if not _requiere_admin_roles(request):
            messages.error(request, 'No tienes permiso para gestionar roles.')
            return redirect('/dashboard/')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        roles = list(Rol.objects.all().order_by('es_sistema', 'nombre'))
        # Contar usuarios por rol y agregarlo como atributo
        for r in roles:
            r.num_usuarios = Usuario.objects.filter(rol_sistema=r.codigo).count()
        return TemplateResponse(request, self.template_name, {
            'roles': roles,
            'areas_disponibles': dict(TODAS_LAS_AREAS),
        })


class CrearEditarRolView(LoginRequiredMixin, View):
    template_name = 'usuarios/form_rol.html'

    def dispatch(self, request, *args, **kwargs):
        if not _requiere_admin_roles(request):
            messages.error(request, 'No tienes permiso para gestionar roles.')
            return redirect('/dashboard/')
        return super().dispatch(request, *args, **kwargs)

    def _get_rol(self, pk):
        if pk:
            return get_object_or_404(Rol, pk=pk)
        return None

    def get(self, request, pk=None, **_):
        rol = self._get_rol(pk)
        form = RolForm(instance=rol)
        areas_seleccionadas = set(rol.areas_permitidas) if rol else set()
        return TemplateResponse(request, self.template_name, {
            'form': form,
            'rol': rol,
            'es_nuevo': not rol,
            'todas_las_areas': TODAS_LAS_AREAS,
            'areas_seleccionadas': areas_seleccionadas,
        })

    def post(self, request, pk=None, **_):
        rol = self._get_rol(pk)
        form = RolForm(request.POST or None, instance=rol)
        # Obtener áreas marcadas en el formulario
        areas_marcadas = []
        for area_codigo, _ in TODAS_LAS_AREAS:
            if request.POST.get(f'area_{area_codigo}'):
                areas_marcadas.append(area_codigo)

        if form.is_valid():
            rol_guardado = form.save(commit=False)
            rol_guardado.areas_permitidas = areas_marcadas
            # Si es nuevo, no es rol del sistema
            if not rol_guardado.pk:
                rol_guardado.es_sistema = False
            rol_guardado.save()
            # Invalida la caché de la matriz de accesos
            recargar_matriz_roles()
            messages.success(request, f'✅ Rol "{rol_guardado.nombre}" guardado correctamente.')
            return redirect('usuarios:lista_roles')
        areas_seleccionadas = set(areas_marcadas)
        return TemplateResponse(request, self.template_name, {
            'form': form,
            'rol': rol,
            'es_nuevo': not rol,
            'todas_las_areas': TODAS_LAS_AREAS,
            'areas_seleccionadas': areas_seleccionadas,
        })


class EliminarRolView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not _requiere_admin_roles(request):
            messages.error(request, 'No tienes permiso para gestionar roles.')
            return redirect('/dashboard/')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, **_):
        rol = get_object_or_404(Rol, pk=pk)
        if rol.es_sistema:
            messages.error(request, '❌ No se pueden eliminar los roles integrados del sistema.')
            return redirect('usuarios:lista_roles')
        # Verificar si hay usuarios con este rol
        num_usuarios = Usuario.objects.filter(rol_sistema=rol.codigo).count()
        if num_usuarios > 0:
            messages.error(
                request,
                f'❌ No se puede eliminar: hay {num_usuarios} usuario(s) con este rol. '
                f'Cámbieles el rol primero.'
            )
            return redirect('usuarios:lista_roles')
        nombre = rol.nombre
        rol.delete()
        recargar_matriz_roles()
        messages.success(request, f'✅ Rol "{nombre}" eliminado correctamente.')
        return redirect('usuarios:lista_roles')

