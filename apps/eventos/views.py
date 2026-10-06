from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import EventoForm, TipoIdentificacionForm, TipoServicioForm
from .models import Evento, TipoIdentificacion, TipoServicio


class EventoListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Evento
    template_name = 'eventos/lista.html'
    context_object_name = 'eventos'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '').strip()
        municipio = self.request.GET.get('municipio', '').strip()
        activo = self.request.GET.get('activo', '')

        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(lugar__icontains=q)
            )
        if estado:
            queryset = queryset.filter(estado=estado)
        if municipio:
            queryset = queryset.filter(municipio__icontains=municipio)
        if activo in ['1', '0']:
            queryset = queryset.filter(activo=(activo == '1'))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['estado'] = self.request.GET.get('estado', '')
        context['municipio'] = self.request.GET.get('municipio', '')
        context['activo'] = self.request.GET.get('activo', '')
        context['estados_choices'] = Evento.ESTADOS
        context['total'] = self.get_queryset().count()
        context['tipos_identificacion'] = TipoIdentificacion.objects.order_by('nombre')
        return context


class EventoCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = 'eventos/_form.html'
    success_url = reverse_lazy('eventos:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, 'Evento creado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Evento'
        context['submit_label'] = 'Crear Evento'
        context['cancel_url'] = reverse_lazy('eventos:list')
        return context


class EventoUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = 'eventos/_form.html'
    success_url = reverse_lazy('eventos:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, 'Evento actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Evento'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('eventos:list')
        return context


class EventoDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Evento
    template_name = 'eventos/detalle.html'
    context_object_name = 'evento'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_servicio'] = self.object.tipos_servicio.order_by('orden', 'nombre')
        context['proyectos_count'] = self.object.proyectos.count()
        context['servicio_form'] = TipoServicioForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = TipoServicioForm(request.POST)
        if form.is_valid():
            servicio = form.save(commit=False)
            servicio.evento = self.object
            servicio.save()
            messages.success(request, f'Tipo de servicio "{servicio.nombre}" agregado correctamente.')
            return HttpResponseRedirect(reverse('eventos:detail', args=[self.object.pk]))
        messages.error(request, 'Error al agregar el tipo de servicio.')
        return self.render_to_response(self.get_context_data(servicio_form=form))


class EventoDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Evento
    template_name = 'eventos/detalle.html'
    success_url = reverse_lazy('eventos:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Evento eliminado correctamente.')
        return super().delete(request, *args, **kwargs)


class EventoToggleActivoView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def post(self, request, pk, *args, **kwargs):
        evento = get_object_or_404(Evento, pk=pk)
        evento.activo = not evento.activo
        evento.save()
        estado = 'activado' if evento.activo else 'desactivado'
        messages.success(request, f'Evento {estado} correctamente.')
        return HttpResponseRedirect(reverse('eventos:detail', args=[pk]))


class ServicioToggleActivoView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def post(self, request, evento_pk, servicio_pk, *args, **kwargs):
        servicio = get_object_or_404(TipoServicio, pk=servicio_pk, evento_id=evento_pk)
        servicio.activo = not servicio.activo
        servicio.save()
        estado = 'activado' if servicio.activo else 'desactivado'
        messages.success(request, f'Servicio "{servicio.nombre}" {estado} correctamente.')
        return HttpResponseRedirect(reverse('eventos:detail', args=[evento_pk]))


class ServicioDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR']

    def post(self, request, evento_pk, servicio_pk, *args, **kwargs):
        servicio = get_object_or_404(TipoServicio, pk=servicio_pk, evento_id=evento_pk)
        nombre = servicio.nombre
        servicio.delete()
        messages.success(request, f'Tipo de servicio "{nombre}" eliminado correctamente.')
        return HttpResponseRedirect(reverse('eventos:detail', args=[evento_pk]))


class TipoIdentificacionListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = TipoIdentificacion
    template_name = 'eventos/tipos_identificacion.html'
    context_object_name = 'tipos'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        return super().get_queryset().order_by('nombre')


class TipoIdentificacionCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = TipoIdentificacion
    form_class = TipoIdentificacionForm
    template_name = 'eventos/_form_tipo.html'
    success_url = reverse_lazy('eventos:tipos_identificacion_list')
    roles_requeridos = ['ADMINISTRADOR']

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de identificación creado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Tipo de Identificación'
        context['submit_label'] = 'Crear Tipo'
        context['cancel_url'] = reverse_lazy('eventos:tipos_identificacion_list')
        context['back_url'] = reverse_lazy('eventos:list')
        return context


class TipoIdentificacionUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = TipoIdentificacion
    form_class = TipoIdentificacionForm
    template_name = 'eventos/_form_tipo.html'
    success_url = reverse_lazy('eventos:tipos_identificacion_list')
    roles_requeridos = ['ADMINISTRADOR']

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de identificación actualizado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Identificación'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('eventos:tipos_identificacion_list')
        context['back_url'] = reverse_lazy('eventos:list')
        return context
