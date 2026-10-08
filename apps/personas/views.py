from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.core.mixins import RoleRequiredMixin
from .forms import PersonaForm
from .models import Persona


class PersonaListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Persona
    template_name = 'personas/lista.html'
    context_object_name = 'personas'
    paginate_by = 15
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('tipo_identificacion', 'creado_por')
        q = self.request.GET.get('q', '').strip()
        tipo_persona = self.request.GET.get('tipo_persona', '').strip()
        activo = self.request.GET.get('activo', '')

        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(numero_identificacion__icontains=q) |
                Q(correo__icontains=q)
            )
        if tipo_persona:
            queryset = queryset.filter(tipo_persona=tipo_persona)
        if activo in ['1', '0']:
            queryset = queryset.filter(activo=(activo == '1'))

        return queryset.order_by('apellidos', 'nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['tipo_persona'] = self.request.GET.get('tipo_persona', '')
        context['activo'] = self.request.GET.get('activo', '')
        context['tipos_choices'] = Persona.TIPOS
        context['total'] = self.get_queryset().count()
        return context


class PersonaCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'personas/_form.html'
    success_url = reverse_lazy('personas:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    @transaction.atomic
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        self.object = form.save()

        if form.cleaned_data.get('crear_perfil'):
            tipo = form.cleaned_data.get('tipo_persona')
            self._crear_perfil_asociado(form, tipo)

        messages.success(self.request, f'Persona {self.object.nombre_completo} registrada correctamente.')
        return super().form_valid(form)

    def _crear_perfil_asociado(self, form, tipo):
        from apps.instructores.models import Instructor
        from apps.invitados.models import Invitado
        from apps.proyectos.models import Aprendiz
        from apps.organizadores.models import Organizador

        if tipo == 'INSTRUCTOR':
            programas = form.cleaned_data.get('programas', [])
            instructor, created = Instructor.objects.get_or_create(
                persona=self.object,
                defaults={'activo': True},
            )
            if programas:
                instructor.programas.set(programas)
            if created:
                messages.info(self.request, 'Perfil de Instructor creado correctamente.')
            else:
                messages.info(self.request, 'Perfil de Instructor ya existía, programas actualizados.')

        elif tipo == 'INVITADO':
            entidad = form.cleaned_data.get('entidad')
            cargo = form.cleaned_data.get('cargo')
            Invitado.objects.update_or_create(
                persona=self.object,
                defaults={'entidad': entidad, 'cargo': cargo},
            )
            messages.info(self.request, 'Perfil de Invitado creado correctamente.')

        elif tipo == 'ORGANIZADOR':
            cargo = form.cleaned_data.get('cargo_organizador') or None
            area = form.cleaned_data.get('area_organizador') or None
            Organizador.objects.update_or_create(
                persona=self.object,
                defaults={'cargo': cargo, 'area_responsabilidad': area, 'activo': True},
            )
            messages.info(self.request, 'Perfil de Organizador creado correctamente.')

        elif tipo == 'APRENDIZ':
            proyecto = form.cleaned_data.get('proyecto')
            grado = form.cleaned_data.get('grado') or '11'
            if proyecto:
                Aprendiz.objects.update_or_create(
                    persona=self.object,
                    defaults={'proyecto': proyecto, 'grado': grado},
                )
                messages.info(self.request, f'Perfil de Aprendiz creado y asociado al proyecto {proyecto.codigo}.')
            else:
                messages.warning(
                    self.request,
                    'No se pudo crear perfil de Aprendiz: no se seleccionó un proyecto. Puede asignarlo luego desde Proyectos.'
                )

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Persona / Participante'
        context['submit_label'] = 'Registrar Persona'
        context['cancel_url'] = reverse_lazy('personas:list')
        return context


class PersonaUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'personas/_form.html'
    success_url = reverse_lazy('personas:list')
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_initial(self):
        initial = super().get_initial()
        persona = self.object
        from apps.instructores.models import Instructor
        from apps.invitados.models import Invitado
        from apps.proyectos.models import Aprendiz
        from apps.organizadores.models import Organizador

        if hasattr(persona, 'perfil_instructor'):
            initial['programas'] = persona.perfil_instructor.programas.values_list('pk', flat=True)
        if hasattr(persona, 'perfil_invitado'):
            initial['entidad'] = persona.perfil_invitado.entidad
            initial['cargo'] = persona.perfil_invitado.cargo
        if hasattr(persona, 'perfil_aprendiz'):
            initial['proyecto'] = persona.perfil_aprendiz.proyecto_id
            initial['grado'] = persona.perfil_aprendiz.grado
        if hasattr(persona, 'perfil_organizador'):
            initial['cargo_organizador'] = persona.perfil_organizador.cargo
            initial['area_organizador'] = persona.perfil_organizador.area_responsabilidad
        return initial

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        if form.cleaned_data.get('crear_perfil'):
            tipo = form.cleaned_data.get('tipo_persona')
            self._actualizar_perfil_asociado(form, tipo)
        messages.success(self.request, f'Persona {self.object.nombre_completo} actualizada correctamente.')
        return super().form_valid(form)

    def _actualizar_perfil_asociado(self, form, tipo):
        from apps.instructores.models import Instructor
        from apps.invitados.models import Invitado
        from apps.proyectos.models import Aprendiz
        from apps.organizadores.models import Organizador

        if tipo == 'INSTRUCTOR':
            programas = form.cleaned_data.get('programas', [])
            instructor, _ = Instructor.objects.get_or_create(
                persona=self.object, defaults={'activo': True}
            )
            instructor.activo = True
            instructor.save()
            instructor.programas.set(programas)

        elif tipo == 'INVITADO':
            Invitado.objects.update_or_create(
                persona=self.object,
                defaults={
                    'entidad': form.cleaned_data.get('entidad'),
                    'cargo': form.cleaned_data.get('cargo'),
                },
            )

        elif tipo == 'ORGANIZADOR':
            Organizador.objects.update_or_create(
                persona=self.object,
                defaults={
                    'cargo': form.cleaned_data.get('cargo_organizador') or None,
                    'area_responsabilidad': form.cleaned_data.get('area_organizador') or None,
                    'activo': True,
                },
            )

        elif tipo == 'APRENDIZ':
            proyecto = form.cleaned_data.get('proyecto')
            grado = form.cleaned_data.get('grado') or '11'
            if proyecto:
                Aprendiz.objects.update_or_create(
                    persona=self.object,
                    defaults={'proyecto': proyecto, 'grado': grado},
                )

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor revise los errores del formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Persona'
        context['submit_label'] = 'Guardar Cambios'
        context['cancel_url'] = reverse_lazy('personas:list')
        return context


class PersonaDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Persona
    template_name = 'personas/detalle.html'
    context_object_name = 'persona'
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PersonaDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Persona
    template_name = 'personas/detalle.html'
    success_url = reverse_lazy('personas:list')
    roles_requeridos = ['ADMINISTRADOR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context

    def delete(self, request, *args, **kwargs):
        nombre = self.get_object().nombre_completo
        messages.success(request, f'Persona "{nombre}" eliminada correctamente.')
        return super().delete(request, *args, **kwargs)
