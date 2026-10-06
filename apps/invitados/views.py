from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import InvitadoForm
from .models import Invitado


class InvitadoListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Invitado
    template_name = 'invitados/lista.html'
    context_object_name = 'invitados'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'persona', 'persona__tipo_identificacion'
        )
        q = self.request.GET.get('q', '').strip()
        entidad = self.request.GET.get('entidad', '').strip()

        if q:
            queryset = queryset.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__numero_identificacion__icontains=q) |
                Q(persona__correo__icontains=q) |
                Q(cargo__icontains=q)
            )
        if entidad:
            queryset = queryset.filter(entidad__icontains=entidad)

        return queryset.order_by('persona__apellidos', 'persona__nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['entidad'] = self.request.GET.get('entidad', '')
        context['total'] = self.get_queryset().count()
        return context


class InvitadoCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Invitado
    form_class = InvitadoForm
    template_name = 'invitados/_form.html'
    success_url = reverse_lazy('invitados:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Invitado {form.instance.persona.nombre_completo} registrado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Invitado'
        context['submit_label'] = 'Crear Invitado'
        context['cancel_url'] = reverse_lazy('invitados:list')
        return context


class InvitadoUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Invitado
    form_class = InvitadoForm
    template_name = 'invitados/_form.html'
    success_url = reverse_lazy('invitados:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Invitado {form.instance.persona.nombre_completo} actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Invitado'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('invitados:list')
        return context


class InvitadoDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Invitado
    template_name = 'invitados/detalle.html'
    context_object_name = 'invitado'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']


class InvitadoDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Invitado
    template_name = 'invitados/detalle.html'
    success_url = reverse_lazy('invitados:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        nombre = str(obj.persona.nombre_completo)
        messages.success(request, f'Invitado "{nombre}" eliminado correctamente.')
        return super().delete(request, *args, **kwargs)
