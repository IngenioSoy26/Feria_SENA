from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import ProgramaForm
from .models import ProgramaTecnico


class ProgramaListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = ProgramaTecnico
    template_name = 'programas/lista.html'
    context_object_name = 'programas'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        activo = self.request.GET.get('activo', '')

        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(codigo__icontains=q)
            )
        if activo in ['1', '0']:
            queryset = queryset.filter(activo=(activo == '1'))

        return queryset.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['activo'] = self.request.GET.get('activo', '')
        context['total'] = self.get_queryset().count()
        return context


class ProgramaCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = ProgramaTecnico
    form_class = ProgramaForm
    template_name = 'programas/_form.html'
    success_url = reverse_lazy('programas:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, 'Programa técnico creado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Programa Técnico'
        context['submit_label'] = 'Crear Programa'
        context['cancel_url'] = reverse_lazy('programas:list')
        return context


class ProgramaUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = ProgramaTecnico
    form_class = ProgramaForm
    template_name = 'programas/_form.html'
    success_url = reverse_lazy('programas:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, 'Programa técnico actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Programa Técnico'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('programas:list')
        return context


class ProgramaDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = ProgramaTecnico
    template_name = 'programas/detalle.html'
    context_object_name = 'programa'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proyectos_relacionados'] = self.object.proyectos.select_related(
            'institucion', 'instructor_responsable', 'evento'
        ).all()[:20]
        context['instructores_relacionados'] = self.object.instructores.select_related(
            'persona'
        ).all()[:20]
        return context


class ProgramaDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = ProgramaTecnico
    template_name = 'programas/detalle.html'
    success_url = reverse_lazy('programas:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Programa técnico eliminado correctamente.')
        return super().delete(request, *args, **kwargs)
