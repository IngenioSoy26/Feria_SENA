import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages

from apps.core.mixins import RoleRequiredMixin
from apps.escarapelas.services import EscarapelaPDFService
from apps.eventos.models import Evento
from apps.instituciones.models import InstitucionEducativa
from apps.personas.models import Persona
from apps.programas.models import ProgramaTecnico
from apps.proyectos.models import Proyecto


ROLES_PERMITIDOS = ['ADMINISTRADOR', 'REGISTRO']


def _construir_nombre_archivo(prefijo):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{prefijo}_{ts}.pdf'


def _respuesta_pdf(buffer, nombre_archivo):
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf',
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


class EscarapelaInicioView(RoleRequiredMixin, TemplateView):
    template_name = 'escarapelas/inicio.html'
    roles_requeridos = ROLES_PERMITIDOS

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        eventos = Evento.objects.filter(activo=True).order_by('-fecha_inicio')
        ctx['eventos'] = eventos
        ctx['evento_seleccionado'] = (
            eventos.filter(estado='ACTIVO').first()
            or eventos.first()
        )
        evento_id = self.request.GET.get('evento', ctx['evento_seleccionado'].id if ctx['evento_seleccionado'] else None)
        if evento_id:
            try:
                ctx['evento_seleccionado'] = eventos.get(id=evento_id)
            except (Evento.DoesNotExist, ValueError):
                pass

        ev = ctx['evento_seleccionado']
        if ev:
            ctx['personas'] = Persona.objects.filter(activo=True).order_by('apellidos', 'nombres')[:200]
            ctx['proyectos'] = Proyecto.objects.filter(evento=ev).select_related('institucion', 'programa').order_by('codigo')
            ctx['instituciones'] = InstitucionEducativa.objects.filter(
                proyectos__evento=ev, activo=True
            ).distinct().order_by('nombre')
            ctx['programas'] = ProgramaTecnico.objects.filter(
                proyectos__evento=ev, activo=True
            ).distinct().order_by('codigo')
            ctx['tipos_persona'] = Persona.TIPOS
        return ctx


class EscarapelaDescargaIndividualView(RoleRequiredMixin, View):
    roles_requeridos = ROLES_PERMITIDOS

    def get(self, request, persona_id):
        persona = get_object_or_404(Persona, id=persona_id)
        evento = (
            Evento.objects.filter(activo=True, estado='ACTIVO').first()
            or Evento.objects.filter(activo=True).first()
        )
        buffer = EscarapelaPDFService.generar_individual(persona, evento)
        slug = (persona.nombre_completo.lower().replace(' ', '_')[:30]) or 'persona'
        return _respuesta_pdf(buffer, _construir_nombre_archivo(f'escarapela_{slug}'))


class EscarapelaDescargaProyectoView(RoleRequiredMixin, View):
    roles_requeridos = ROLES_PERMITIDOS

    def get(self, request, proyecto_id):
        proyecto = get_object_or_404(Proyecto.objects.select_related('evento'), id=proyecto_id)
        buffer = EscarapelaPDFService.generar_por_proyecto(proyecto)
        return _respuesta_pdf(buffer, _construir_nombre_archivo(f'escarapelas_proyecto_{proyecto.codigo}'))


class EscarapelaDescargaInstitucionView(RoleRequiredMixin, View):
    roles_requeridos = ROLES_PERMITIDOS

    def get(self, request, institucion_id):
        ie = get_object_or_404(InstitucionEducativa, id=institucion_id)
        evento = (
            Evento.objects.filter(activo=True, estado='ACTIVO').first()
            or Evento.objects.filter(activo=True).first()
        )
        buffer = EscarapelaPDFService.generar_por_institucion(ie, evento)
        return _respuesta_pdf(buffer, _construir_nombre_archivo(f'escarapelas_ie_{ie.codigo}'))


class EscarapelaDescargaProgramaView(RoleRequiredMixin, View):
    roles_requeridos = ROLES_PERMITIDOS

    def get(self, request, programa_id):
        programa = get_object_or_404(ProgramaTecnico, id=programa_id)
        evento = (
            Evento.objects.filter(activo=True, estado='ACTIVO').first()
            or Evento.objects.filter(activo=True).first()
        )
        buffer = EscarapelaPDFService.generar_por_programa(programa, evento)
        return _respuesta_pdf(buffer, _construir_nombre_archivo(f'escarapelas_programa_{programa.codigo}'))


class EscarapelaDescargaTipoView(RoleRequiredMixin, View):
    roles_requeridos = ROLES_PERMITIDOS

    def get(self, request, tipo):
        from django.db.models import Q
        evento = (
            Evento.objects.filter(activo=True, estado='ACTIVO').first()
            or Evento.objects.filter(activo=True).first()
        )
        if evento:
            proyectos = list(Proyecto.objects.filter(evento=evento).values_list('id', flat=True))
            instructores_proyectos = list(
                Proyecto.objects.filter(evento=evento)
                .exclude(instructor_responsable__isnull=True)
                .values_list('instructor_responsable__persona_id', flat=True)
            )
            qs = Persona.objects.filter(
                activo=True,
                tipo_persona=tipo,
            ).filter(
                Q(perfil_aprendiz__proyecto_id__in=proyectos)
                | Q(id__in=instructores_proyectos)
                | Q(tipo_persona__in=['INVITADO', 'ORGANIZADOR'])
            ).distinct().order_by('apellidos', 'nombres')
        else:
            qs = Persona.objects.filter(activo=True, tipo_persona=tipo).order_by('apellidos', 'nombres')

        buffer = EscarapelaPDFService.generar_lote(qs, evento, f'Tipo {tipo}')
        return _respuesta_pdf(buffer, _construir_nombre_archivo(f'escarapelas_{tipo.lower()}'))


class EscarapelaDescargaCompletaView(RoleRequiredMixin, View):
    roles_requeridos = ROLES_PERMITIDOS

    def get(self, request, evento_id=None):
        if evento_id:
            evento = get_object_or_404(Evento, id=evento_id)
        else:
            evento = (
                Evento.objects.filter(activo=True, estado='ACTIVO').first()
                or Evento.objects.filter(activo=True).first()
            )
        if not evento:
            messages.error(request, 'No hay eventos activos.')
            return redirect(reverse('escarapelas:listar'))
        buffer = EscarapelaPDFService.generar_completo(evento)
        return _respuesta_pdf(buffer, _construir_nombre_archivo(f'escarapelas_evento_{evento.id}'))
