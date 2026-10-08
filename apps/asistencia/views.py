import json
import uuid
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView, FormView
from django import forms

from apps.core.mixins import RoleRequiredMixin, AjaxPermissionRequiredMixin
from apps.core.services import AuditoriaService
from apps.eventos.models import Evento
from apps.personas.models import Persona
from apps.asistencia.models import AsistenciaEvento


ROLES_COLOR = {
    'APRENDIZ': '#39A900',
    'INSTRUCTOR': '#0067B1',
    'INVITADO': '#F57C00',
    'ORGANIZADOR': '#7B1FA2',
}

ROLES_TEXTO = {
    'APRENDIZ': 'Aprendiz',
    'INSTRUCTOR': 'Instructor',
    'INVITADO': 'Invitado',
    'ORGANIZADOR': 'Organizador',
}


def _obtener_evento_activo():
    return Evento.objects.filter(estado='ACTIVO', activo=True).order_by('-fecha_inicio').first()


def _datos_persona_serializados(persona):
    institucion = ''
    programa = ''
    proyecto = ''

    if persona.tipo_persona == 'APRENDIZ':
        aprendiz = getattr(persona, 'perfil_aprendiz', None)
        if aprendiz and aprendiz.proyecto:
            proyecto = str(aprendiz.proyecto.nombre)
            if aprendiz.proyecto.programa:
                programa = str(aprendiz.proyecto.programa.nombre)
            if aprendiz.proyecto.institucion:
                institucion = str(aprendiz.proyecto.institucion.nombre)
    elif persona.tipo_persona == 'INSTRUCTOR':
        instructor = getattr(persona, 'perfil_instructor', None)
        if instructor:
            programas_list = list(instructor.programas.values_list('nombre', flat=True))
            if programas_list:
                programa = programas_list[0]
            institucion = 'SENA'
    elif persona.tipo_persona == 'INVITADO':
        invitado = getattr(persona, 'perfil_invitado', None)
        if invitado:
            institucion = invitado.entidad
            programa = invitado.cargo or ''
    elif persona.tipo_persona == 'ORGANIZADOR':
        org = getattr(persona, 'perfil_organizador', None)
        if org:
            institucion = org.area_responsabilidad or 'ORGANIZACIÓN'
            programa = org.cargo or 'ORGANIZADOR FERIA'
        else:
            institucion = 'SENA'
            programa = 'ORGANIZADOR'

    return {
        'nombre': persona.nombre_completo,
        'rol_color': ROLES_COLOR.get(persona.tipo_persona, '#424242'),
        'rol_texto': ROLES_TEXTO.get(persona.tipo_persona, persona.tipo_persona),
        'institucion': institucion,
        'programa': programa,
        'proyecto': proyecto,
        'persona_id': persona.id,
    }


def _formato_fecha_hora(dt):
    if not dt:
        return ''
    return dt.strftime('%d/%m/%Y %I:%M %p')


def _registrar_asistencia_logica(request, persona, evento_id, medio='QR'):
    operador = request.user
    try:
        with transaction.atomic():
            asistencia, created = AsistenciaEvento.objects.get_or_create(
                evento_id=evento_id,
                persona=persona,
                defaults={
                    'operador': operador,
                    'medio': medio,
                },
            )
    except IntegrityError:
        asistencia = AsistenciaEvento.objects.filter(
            evento_id=evento_id,
            persona=persona,
        ).select_related('operador').first()
        created = False

    persona_data = _datos_persona_serializados(persona)

    AuditoriaService.registrar(
        request=request,
        usuario=operador,
        accion='ASISTENCIA',
        modulo='ASISTENCIA',
        entidad='AsistenciaEvento',
        id_entidad=asistencia.pk if asistencia else None,
        datos={
            'medio': medio,
            'persona': persona.nombre_completo,
            'persona_id': persona.id,
            'evento_id': evento_id,
            'es_nuevo': bool(created),
        },
    )

    if not created:
        operador_original = ''
        if asistencia and asistencia.operador:
            operador_original = getattr(asistencia.operador, 'nombre_completo', str(asistencia.operador))
        return {
            'status': 'AMARILLO',
            'mensaje': 'INGRESO REGISTRADO ANTERIORMENTE',
            'fecha_hora': _formato_fecha_hora(asistencia.fecha_hora if asistencia else None),
            'operador': operador_original,
            'persona': persona_data,
        }

    return {
        'status': 'VERDE',
        'mensaje': 'INGRESO REGISTRADO',
        'persona': persona_data,
        'fecha_hora': _formato_fecha_hora(asistencia.fecha_hora if asistencia else None),
        'operador': getattr(operador, 'nombre_completo', str(operador)),
    }


class IngresoOperadorView(RoleRequiredMixin, TemplateView):
    roles_requeridos = ['ADMINISTRADOR', 'OPERADOR_ASISTENCIA']
    template_name = 'asistencia/ingreso.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        evento = _obtener_evento_activo()
        hoy = date.today()
        contador_ingresados_hoy = 0
        contador_total_registrados = 0
        evento_id = None
        if evento:
            evento_id = evento.id
            contador_total_registrados = AsistenciaEvento.objects.filter(evento=evento).count()
            contador_ingresados_hoy = AsistenciaEvento.objects.filter(
                evento=evento,
                fecha_hora__date=hoy,
            ).count()
        ctx['evento_activo'] = evento
        ctx['contador_ingresados_hoy'] = contador_ingresados_hoy
        ctx['contador_total_registrados'] = contador_total_registrados
        ctx['evento_id'] = evento_id
        user = self.request.user
        ctx['nombre_operador'] = getattr(user, 'nombre_completo', user.username)
        return ctx


class ValidarTokenAsistenciaJson(AjaxPermissionRequiredMixin, View):
    permission_required = 'asistencia.add_asistenciaevento'
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = request.POST
        token_raw = body.get('token') or body.get('qr_token') or ''
        evento_id = body.get('evento_id')

        if not token_raw:
            return JsonResponse({
                'status': 'ROJO',
                'mensaje': 'Token QR vacío o no proporcionado.',
            }, status=200)

        token_limpio = str(token_raw).strip()
        try:
            token_uuid = uuid.UUID(token_limpio)
        except (ValueError, AttributeError):
            return JsonResponse({
                'status': 'ROJO',
                'mensaje': 'QR inválido o persona no encontrada',
            }, status=200)

        try:
            persona = Persona.objects.select_related(
                'tipo_identificacion',
            ).prefetch_related(
                'perfil_aprendiz__proyecto__institucion',
                'perfil_aprendiz__proyecto__programa',
                'perfil_instructor__programas',
                'perfil_invitado',
            ).get(qr_token=token_uuid, activo=True)
        except Persona.DoesNotExist:
            return JsonResponse({
                'status': 'ROJO',
                'mensaje': 'QR inválido o persona no encontrada',
            }, status=200)

        persona_data = _datos_persona_serializados(persona)
        return JsonResponse({
            'status': 'OK',
            'persona': persona_data,
            'evento_id': evento_id,
        }, status=200)


class RegistrarAsistenciaJson(AjaxPermissionRequiredMixin, View):
    permission_required = 'asistencia.add_asistenciaevento'
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = request.POST
        token_raw = body.get('token') or body.get('qr_token') or ''
        persona_id = body.get('persona_id')
        evento_id = body.get('evento_id')
        medio = str(body.get('medio', 'QR')).upper()
        if medio not in ('QR', 'MANUAL'):
            medio = 'QR'

        if not evento_id:
            evento = _obtener_evento_activo()
            if evento:
                evento_id = evento.id

        if not evento_id:
            return JsonResponse({
                'status': 'ROJO',
                'mensaje': 'No hay un evento activo configurado.',
            }, status=200)

        persona = None
        if persona_id:
            try:
                persona = Persona.objects.select_related(
                    'tipo_identificacion',
                ).prefetch_related(
                    'perfil_aprendiz__proyecto__institucion',
                    'perfil_aprendiz__proyecto__programa',
                    'perfil_instructor__programas',
                    'perfil_invitado',
                ).get(id=persona_id, activo=True)
            except Persona.DoesNotExist:
                persona = None

        if persona is None and token_raw:
            token_limpio = str(token_raw).strip()
            try:
                token_uuid = uuid.UUID(token_limpio)
                try:
                    persona = Persona.objects.select_related(
                        'tipo_identificacion',
                    ).prefetch_related(
                        'perfil_aprendiz__proyecto__institucion',
                        'perfil_aprendiz__proyecto__programa',
                        'perfil_instructor__programas',
                        'perfil_invitado',
                    ).get(qr_token=token_uuid, activo=True)
                except Persona.DoesNotExist:
                    persona = None
            except (ValueError, AttributeError):
                persona = None

        if persona is None:
            return JsonResponse({
                'status': 'ROJO',
                'mensaje': 'QR inválido o persona no encontrada',
            }, status=200)

        resultado = _registrar_asistencia_logica(request, persona, evento_id, medio=medio)
        return JsonResponse(resultado, status=200)


class BusquedaPersonaForm(forms.Form):
    criterio = forms.CharField(
        required=True,
        max_length=120,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Número de identificación o nombre',
            'autocomplete': 'off',
        }),
    )


class BuscarManualAsistenciaView(RoleRequiredMixin, FormView):
    roles_requeridos = ['ADMINISTRADOR', 'OPERADOR_ASISTENCIA']
    template_name = 'asistencia/buscar_manual.html'
    form_class = BusquedaPersonaForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        evento = _obtener_evento_activo()
        ctx['evento_activo'] = evento
        ctx['evento_id'] = evento.id if evento else None
        user = self.request.user
        ctx['nombre_operador'] = getattr(user, 'nombre_completo', user.username)
        ctx['resultados'] = kwargs.get('resultados', [])
        ctx['resultado_registro'] = kwargs.get('resultado_registro')
        return ctx

    def _buscar_personas(self, criterio):
        qs = Persona.objects.filter(activo=True).select_related(
            'tipo_identificacion',
        ).prefetch_related(
            'perfil_aprendiz__proyecto__institucion',
            'perfil_aprendiz__proyecto__programa',
            'perfil_instructor__programas',
            'perfil_invitado',
        )
        if criterio.isdigit():
            qs = qs.filter(numero_identificacion__icontains=criterio)
        else:
            qs = qs.filter(
                Q(nombres__icontains=criterio) | Q(apellidos__icontains=criterio)
            )
        return qs.order_by('apellidos', 'nombres')[:50]

    def get(self, request, *args, **kwargs):
        resultados = []
        criterio = request.GET.get('criterio', '').strip()
        if criterio:
            resultados = self._buscar_personas(criterio)
        ctx = self.get_context_data(resultados=resultados)
        ctx['criterio'] = criterio
        return self.render_to_response(ctx)

    def post(self, request, *args, **kwargs):
        if 'registrar' in request.POST:
            return self._registrar_manual(request)
        criterio = request.POST.get('criterio', '').strip()
        resultados = []
        if criterio:
            resultados = self._buscar_personas(criterio)
        ctx = self.get_context_data(resultados=resultados)
        ctx['criterio'] = criterio
        return self.render_to_response(ctx)

    def _registrar_manual(self, request):
        persona_id = request.POST.get('persona_id')
        evento_id = request.POST.get('evento_id')
        resultado_registro = None

        if not persona_id:
            ctx = self.get_context_data(resultados=[])
            ctx['error_registro'] = 'Debe seleccionar una persona.'
            ctx['criterio'] = request.POST.get('criterio', '')
            return self.render_to_response(ctx)

        if not evento_id:
            evento = _obtener_evento_activo()
            if evento:
                evento_id = evento.id

        if not evento_id:
            resultado_registro = {
                'status': 'ROJO',
                'mensaje': 'No hay un evento activo configurado.',
            }
        else:
            try:
                persona = Persona.objects.select_related(
                    'tipo_identificacion',
                ).prefetch_related(
                    'perfil_aprendiz__proyecto__institucion',
                    'perfil_aprendiz__proyecto__programa',
                    'perfil_instructor__programas',
                    'perfil_invitado',
                ).get(id=persona_id, activo=True)
                resultado_registro = _registrar_asistencia_logica(
                    request, persona, int(evento_id), medio='MANUAL'
                )
            except Persona.DoesNotExist:
                resultado_registro = {
                    'status': 'ROJO',
                    'mensaje': 'Persona no encontrada o inactiva.',
                }

        ctx = self.get_context_data(
            resultados=[],
            resultado_registro=resultado_registro,
        )
        ctx['criterio'] = request.POST.get('criterio', '')
        return self.render_to_response(ctx)
