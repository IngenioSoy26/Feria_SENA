from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import InstructorForm
from .models import Instructor


class InstructorListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Instructor
    template_name = 'instructores/lista.html'
    context_object_name = 'instructores'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'persona', 'persona__tipo_identificacion'
        ).prefetch_related('programas').annotate(
            num_proyectos=Count('proyectos_dirigidos', distinct=True)
        )
        q = self.request.GET.get('q', '').strip()
        programa = self.request.GET.get('programa', '').strip()
        activo = self.request.GET.get('activo', '')

        if q:
            queryset = queryset.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__numero_identificacion__icontains=q) |
                Q(persona__correo__icontains=q)
            )
        if programa:
            queryset = queryset.filter(programas__pk=programa).distinct()
        if activo in ['1', '0']:
            queryset = queryset.filter(activo=(activo == '1'))

        return queryset.order_by('persona__apellidos', 'persona__nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.programas.models import ProgramaTecnico
        context['q'] = self.request.GET.get('q', '')
        context['programa'] = self.request.GET.get('programa', '')
        context['activo'] = self.request.GET.get('activo', '')
        context['programas_list'] = ProgramaTecnico.objects.filter(activo=True).order_by('nombre')
        context['total'] = self.get_queryset().count()
        return context


class InstructorCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Instructor
    form_class = InstructorForm
    template_name = 'instructores/_form.html'
    success_url = reverse_lazy('instructores:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Instructor {form.instance.persona.nombre_completo} registrado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Instructor'
        context['submit_label'] = 'Crear Instructor'
        context['cancel_url'] = reverse_lazy('instructores:list')
        return context


class InstructorUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Instructor
    form_class = InstructorForm
    template_name = 'instructores/_form.html'
    success_url = reverse_lazy('instructores:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Instructor {form.instance.persona.nombre_completo} actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Instructor'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('instructores:list')
        return context


class InstructorDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Instructor
    template_name = 'instructores/detalle.html'
    context_object_name = 'instructor'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proyectos_dirigidos'] = self.object.proyectos_dirigidos.select_related(
            'evento', 'institucion', 'programa'
        ).all()[:20]
        return context


class InstructorDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Instructor
    template_name = 'instructores/detalle.html'
    success_url = reverse_lazy('instructores:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        nombre = str(obj.persona.nombre_completo)
        messages.success(request, f'Instructor "{nombre}" eliminado correctamente.')
        return super().delete(request, *args, **kwargs)
