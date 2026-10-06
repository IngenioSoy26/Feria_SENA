from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import InstitucionForm
from .models import InstitucionEducativa


class InstitucionListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = InstitucionEducativa
    template_name = 'instituciones/lista.html'
    context_object_name = 'instituciones'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        municipio = self.request.GET.get('municipio', '').strip()
        activo = self.request.GET.get('activo', '')

        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(codigo__icontains=q)
            )
        if municipio:
            queryset = queryset.filter(municipio__icontains=municipio)
        if activo in ['1', '0']:
            queryset = queryset.filter(activo=(activo == '1'))

        return queryset.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['municipio'] = self.request.GET.get('municipio', '')
        context['activo'] = self.request.GET.get('activo', '')
        context['total'] = self.get_queryset().count()
        return context


class InstitucionCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = InstitucionEducativa
    form_class = InstitucionForm
    template_name = 'instituciones/_form.html'
    success_url = reverse_lazy('instituciones:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, 'Institución creada correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Institución'
        context['submit_label'] = 'Crear Institución'
        context['cancel_url'] = reverse_lazy('instituciones:list')
        return context


class InstitucionUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = InstitucionEducativa
    form_class = InstitucionForm
    template_name = 'instituciones/_form.html'
    success_url = reverse_lazy('instituciones:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, 'Institución actualizada correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Institución'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('instituciones:list')
        return context


class InstitucionDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = InstitucionEducativa
    template_name = 'instituciones/detalle.html'
    context_object_name = 'institucion'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proyectos_relacionados'] = self.object.proyectos.select_related(
            'programa', 'instructor_responsable'
        ).all()[:20]
        return context


class InstitucionDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = InstitucionEducativa
    template_name = 'instituciones/detalle.html'
    success_url = reverse_lazy('instituciones:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Institución eliminada correctamente.')
        return super().delete(request, *args, **kwargs)
