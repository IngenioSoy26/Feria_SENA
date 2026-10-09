from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.mixins import RoleRequiredMixin
from apps.organizadores.models import Organizador
from apps.personas.forms import PersonaForm
from apps.personas.models import Persona


class OrganizadorListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Organizador
    template_name = 'organizadores/lista.html'
    context_object_name = 'organizadores'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        try:
            qs = super().get_queryset().select_related(
                'persona', 'persona__tipo_identificacion'
            )
            q = self.request.GET.get('q', '').strip()
            activo = self.request.GET.get('activo', '')
            if q:
                qs = qs.filter(
                    Q(persona__nombres__icontains=q)
                    | Q(persona__apellidos__icontains=q)
                    | Q(persona__numero_identificacion__icontains=q)
                    | Q(persona__correo__icontains=q)
                    | Q(cargo__icontains=q)
                    | Q(area_responsabilidad__icontains=q)
                )
            if activo in ('1', '0'):
                qs = qs.filter(activo=(activo == '1'))
            return qs.order_by('persona__apellidos', 'persona__nombres')
        except Exception:
            return Organizador.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['activo'] = self.request.GET.get('activo', '')
        try:
            ctx['total'] = self.get_queryset().count()
        except Exception:
            ctx['total'] = 0
        return ctx


class OrganizadorDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Organizador
    template_name = 'organizadores/detalle.html'
    context_object_name = 'organizador'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        try:
            return super().get_queryset().select_related('persona', 'persona__tipo_identificacion')
        except Exception:
            return Organizador.objects.none()


class OrganizadorCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'personas/_form.html'
    success_url = reverse_lazy('organizadores:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_initial(self):
        initial = super().get_initial()
        initial['tipo_persona'] = 'ORGANIZADOR'
        initial['crear_perfil'] = True
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo Organizador'
        ctx['submit_label'] = 'Registrar Organizador'
        ctx['cancel_url'] = reverse_lazy('organizadores:list')
        return ctx

    def form_valid(self, form):
        form.instance.tipo_persona = 'ORGANIZADOR'
        form.instance.creado_por = self.request.user
        self.object = form.save()
        self._crear_perfil_organizador(form)
        messages.success(self.request, f'Organizador {self.object.nombre_completo} registrado correctamente.')
        from django.shortcuts import redirect
        return redirect(self.success_url)

    def _crear_perfil_organizador(self, form):
        try:
            Organizador.objects.get_or_create(
                persona=self.object,
                defaults={
                    'cargo': form.cleaned_data.get('cargo_organizador') or None,
                    'area_responsabilidad': form.cleaned_data.get('area_organizador') or None,
                },
            )
        except Exception as err:
            messages.warning(
                self.request,
                f'Perfil Organizador: no se pudo crear (¿migración pendiente?). Detalle: {err}',
            )


class OrganizadorUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Organizador
    form_class = PersonaForm
    template_name = 'personas/_form.html'
    success_url = reverse_lazy('organizadores:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_object(self, queryset=None):
        try:
            org = super().get_object(queryset)
            return org.persona
        except Exception:
            return None

    def get_initial(self):
        initial = super().get_initial()
        initial['tipo_persona'] = 'ORGANIZADOR'
        initial['crear_perfil'] = True
        persona = self.object
        try:
            org = getattr(persona, 'perfil_organizador', None)
            if org:
                initial['cargo_organizador'] = org.cargo
                initial['area_organizador'] = org.area_responsabilidad
        except Exception:
            pass
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Editar Organizador'
        ctx['submit_label'] = 'Guardar Organizador'
        ctx['cancel_url'] = reverse_lazy('organizadores:list')
        return ctx

    def form_valid(self, form):
        form.instance.tipo_persona = 'ORGANIZADOR'
        self.object = form.save()
        if form.cleaned_data.get('crear_perfil'):
            try:
                Organizador.objects.update_or_create(
                    persona=self.object,
                    defaults={
                        'cargo': form.cleaned_data.get('cargo_organizador') or None,
                        'area_responsabilidad': form.cleaned_data.get('area_organizador') or None,
                        'activo': True,
                    },
                )
            except Exception as err:
                messages.warning(
                    self.request,
                    f'Perfil Organizador: no se pudo actualizar (¿migración pendiente?). Detalle: {err}',
                )
        messages.success(self.request, f'Organizador {self.object.nombre_completo} actualizado correctamente.')
        from django.shortcuts import redirect
        return redirect(self.success_url)


class OrganizadorDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Organizador
    template_name = 'organizadores/detalle.html'
    success_url = reverse_lazy('organizadores:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Exception:
            return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['confirm_delete'] = True
        return ctx

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj is None:
            messages.warning(request, 'No se encontró el organizador.')
            from django.shortcuts import redirect
            return redirect(self.success_url)
        nombre = str(obj.persona)
        try:
            obj.persona.activo = False
            obj.persona.save(update_fields=['activo'])
            obj.activo = False
            obj.save(update_fields=['activo'])
            messages.success(request, f'Organizador "{nombre}" marcado inactivo.')
        except Exception:
            messages.success(request, f'Organizador "{nombre}" eliminado.')
            return super().delete(request, *args, **kwargs)
        from django.shortcuts import redirect
        return redirect(self.success_url)
