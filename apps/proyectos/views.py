from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import ProyectoForm, AgregarAprendizForm, FichaForm
from .models import Proyecto, Aprendiz, Ficha


class FichaListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Ficha
    template_name = 'proyectos/ficha_lista.html'
    context_object_name = 'fichas'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'institucion', 'programa', 'instructor_lider', 'instructor_lider__persona',
        )
        q = self.request.GET.get('q', '').strip()
        activo = self.request.GET.get('activo', '')
        institucion = self.request.GET.get('institucion', '').strip()
        municipio = self.request.GET.get('municipio', '').strip()

        if q:
            queryset = queryset.filter(
                Q(numero__icontains=q) |
                Q(institucion__nombre__icontains=q) |
                Q(programa__nombre__icontains=q) |
                Q(municipio__icontains=q)
            )
        if activo in ['1', '0']:
            queryset = queryset.filter(activo=(activo == '1'))
        if institucion:
            queryset = queryset.filter(institucion_id=institucion)
        if municipio:
            queryset = queryset.filter(municipio__icontains=municipio)

        return queryset.order_by('numero')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.instituciones.models import InstitucionEducativa

        context['q'] = self.request.GET.get('q', '')
        context['activo'] = self.request.GET.get('activo', '')
        context['institucion'] = self.request.GET.get('institucion', '')
        context['municipio'] = self.request.GET.get('municipio', '')
        context['instituciones_list'] = InstitucionEducativa.objects.filter(activo=True).order_by('nombre')
        context['total'] = self.get_queryset().count()
        return context


class FichaCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Ficha
    form_class = FichaForm
    template_name = 'proyectos/ficha_form.html'
    success_url = reverse_lazy('proyectos:ficha_list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Ficha "{form.instance.numero}" creada correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Ficha'
        context['submit_label'] = 'Crear Ficha'
        context['cancel_url'] = reverse_lazy('proyectos:ficha_list')
        return context


class FichaUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Ficha
    form_class = FichaForm
    template_name = 'proyectos/ficha_form.html'
    success_url = reverse_lazy('proyectos:ficha_list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Ficha "{form.instance.numero}" actualizada correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Ficha'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('proyectos:ficha_list')
        return context


class FichaDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Ficha
    template_name = 'proyectos/ficha_detalle.html'
    context_object_name = 'ficha'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proyectos_asociados'] = self.object.proyectos.select_related(
            'evento', 'institucion', 'programa', 'instructor_responsable',
        ).all()
        return context


class FichaDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Ficha
    template_name = 'proyectos/ficha_detalle.html'
    success_url = reverse_lazy('proyectos:ficha_list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'Ficha "{obj.numero}" eliminada correctamente.')
        return super().delete(request, *args, **kwargs)


class ProyectoListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Proyecto
    template_name = 'proyectos/lista.html'
    context_object_name = 'proyectos'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'evento', 'institucion', 'programa', 'instructor_responsable',
            'instructor_responsable__persona',
        ).annotate(
            num_aprendices=Count('aprendices', distinct=True)
        )
        q = self.request.GET.get('q', '').strip()
        evento = self.request.GET.get('evento', '').strip()
        institucion = self.request.GET.get('institucion', '').strip()
        programa = self.request.GET.get('programa', '').strip()
        instructor = self.request.GET.get('instructor', '').strip()
        estado = self.request.GET.get('estado', '').strip()

        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(codigo__icontains=q) |
                Q(descripcion__icontains=q)
            )
        if evento:
            queryset = queryset.filter(evento_id=evento)
        if institucion:
            queryset = queryset.filter(institucion_id=institucion)
        if programa:
            queryset = queryset.filter(programa_id=programa)
        if instructor:
            queryset = queryset.filter(instructor_responsable_id=instructor)
        if estado:
            queryset = queryset.filter(estado=estado)

        return queryset.order_by('-fecha_creacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.eventos.models import Evento
        from apps.instituciones.models import InstitucionEducativa
        from apps.programas.models import ProgramaTecnico
        from apps.instructores.models import Instructor

        context['q'] = self.request.GET.get('q', '')
        context['evento'] = self.request.GET.get('evento', '')
        context['institucion'] = self.request.GET.get('institucion', '')
        context['programa'] = self.request.GET.get('programa', '')
        context['instructor'] = self.request.GET.get('instructor', '')
        context['estado'] = self.request.GET.get('estado', '')
        context['estados_choices'] = Proyecto.ESTADOS
        context['eventos_list'] = Evento.objects.order_by('-fecha_inicio')
        context['instituciones_list'] = InstitucionEducativa.objects.filter(activo=True).order_by('nombre')
        context['programas_list'] = ProgramaTecnico.objects.filter(activo=True).order_by('nombre')
        context['instructores_list'] = Instructor.objects.filter(
            activo=True
        ).select_related('persona').order_by('persona__apellidos')
        context['total'] = self.get_queryset().count()
        return context


class ProyectoCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Proyecto
    form_class = ProyectoForm
    template_name = 'proyectos/_form.html'
    success_url = reverse_lazy('proyectos:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Proyecto "{form.instance.nombre}" creado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Proyecto'
        context['submit_label'] = 'Crear Proyecto'
        context['cancel_url'] = reverse_lazy('proyectos:list')
        return context


class ProyectoUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Proyecto
    form_class = ProyectoForm
    template_name = 'proyectos/_form.html'
    success_url = reverse_lazy('proyectos:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def form_valid(self, form):
        messages.success(self.request, f'Proyecto "{form.instance.nombre}" actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Proyecto'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('proyectos:list')
        return context


class ProyectoDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Proyecto
    template_name = 'proyectos/detalle.html'
    context_object_name = 'proyecto'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['aprendices'] = self.object.aprendices.select_related(
            'persona', 'persona__tipo_identificacion'
        ).all()
        context['agregar_form'] = AgregarAprendizForm(proyecto=self.object)
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = AgregarAprendizForm(request.POST, proyecto=self.object)

        if 'quitar_aprendiz' in request.POST:
            aprendiz_id = request.POST.get('quitar_aprendiz')
            try:
                aprendiz = get_object_or_404(Aprendiz, pk=aprendiz_id, proyecto=self.object)
                nombre = aprendiz.persona.nombre_completo
                aprendiz.delete()
                messages.success(request, f'Aprendiz "{nombre}" removido del proyecto.')
            except Exception:
                messages.error(request, 'Error al remover aprendiz.')
            return HttpResponseRedirect(reverse('proyectos:detail', args=[self.object.pk]))

        if form.is_valid():
            try:
                if form.cleaned_data.get('crear_persona'):
                    from apps.personas.models import Persona
                    from apps.eventos.models import TipoIdentificacion

                    tipo_default = TipoIdentificacion.objects.filter(activo=True).first()
                    if not tipo_default:
                        messages.error(request, 'No hay tipos de identificación activos. Configure primero en Eventos > Tipos ID.')
                        return self.render_to_response(self.get_context_data(agregar_form=form))

                    persona = Persona.objects.create(
                        tipo_identificacion=tipo_default,
                        numero_identificacion=form.cleaned_data['numero_identificacion'],
                        nombres=form.cleaned_data['nombres'],
                        apellidos=form.cleaned_data['apellidos'],
                        tipo_persona='APRENDIZ',
                        creado_por=request.user,
                    )
                    grado = form.cleaned_data.get('grado') or '11'
                    Aprendiz.objects.create(
                        persona=persona,
                        proyecto=self.object,
                        grado=grado,
                    )
                    messages.success(
                        request,
                        f'Persona y perfil de aprendiz creados: {persona.nombre_completo}. '
                        f'Recuerde actualizar tipo de identificación y datos de contacto desde Personas.'
                    )
                else:
                    persona = form.cleaned_data['persona']
                    grado = form.cleaned_data.get('grado') or '11'
                    Aprendiz.objects.create(
                        persona=persona,
                        proyecto=self.object,
                        grado=grado,
                    )
                    messages.success(request, f'Aprendiz "{persona.nombre_completo}" agregado al proyecto.')
                return HttpResponseRedirect(reverse('proyectos:detail', args=[self.object.pk]))
            except Exception as e:
                messages.error(request, f'Error al agregar aprendiz: {str(e)}')
        else:
            messages.error(request, 'Por favor revise los errores al agregar aprendiz.')

        return self.render_to_response(self.get_context_data(agregar_form=form))


class ProyectoDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Proyecto
    template_name = 'proyectos/detalle.html'
    success_url = reverse_lazy('proyectos:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        nombre = f'{obj.codigo} - {obj.nombre}'
        messages.success(request, f'Proyecto "{nombre}" eliminado correctamente.')
        return super().delete(request, *args, **kwargs)
