import json
import uuid
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import TemplateView, FormView
from django import forms

from apps.core.mixins import RoleRequiredMixin, AjaxPermissionRequiredMixin
from apps.core.services import AuditoriaService
from apps.eventos.models import Evento
from apps.personas.models import Persona
from apps.certificados.models import Certificado


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


def _registrar_certificado_logica(request, persona, evento_id, medio='QR'):
    operador = request.user
    certificado = None
    created = False

    try:
        with transaction.atomic():
            try:
                certificado, created = Certificado.objects.get_or_create(
                    evento_id=evento_id,
                    persona=persona,
                    defaults={
                        'operador': operador,
                        'medio': medio,
                    },
                )
            except IntegrityError:
                certificado = Certificado.objects.filter(
                    evento_id=evento_id,
                    persona=persona,
                ).select_related('operador').first()
                created = False
    except Exception:
        certificado = Certificado.objects.filter(
            evento_id=evento_id,
            persona=persona,
        ).select_related('operador').first()
        created = False

    persona_data = _datos_persona_serializados(persona)
    codigo = certificado.codigo_unico if certificado else ''

    AuditoriaService.registrar(
        request=request,
        usuario=operador,
        accion='CERTIFICADO',
        modulo='CERTIFICADOS',
        entidad='Certificado',
        id_entidad=certificado.pk if certificado else None,
        datos={
            'medio': medio,
            'persona': persona.nombre_completo,
            'persona_id': persona.id,
            'evento_id': evento_id,
            'codigo_unico': codigo,
            'es_nuevo': bool(created),
        },
    )

    if not created:
        operador_original = ''
        if certificado and certificado.operador:
            operador_original = getattr(certificado.operador, 'nombre_completo', str(certificado.operador))
        return {
            'status': 'AMARILLO',
            'mensaje': 'CERTIFICADO ENTREGADO ANTERIORMENTE',
            'fecha_hora': _formato_fecha_hora(certificado.fecha_hora_entrega if certificado else None),
            'operador': operador_original,
            'persona': persona_data,
            'codigo_unico': codigo,
        }

    return {
        'status': 'VERDE',
        'mensaje': 'CERTIFICADO ENTREGADO',
        'persona': persona_data,
        'fecha_hora': _formato_fecha_hora(certificado.fecha_hora_entrega if certificado else None),
        'operador': getattr(operador, 'nombre_completo', str(operador)),
        'codigo_unico': codigo,
    }


class EntregaOperadorView(RoleRequiredMixin, TemplateView):
    roles_requeridos = ['ADMINISTRADOR', 'OPERADOR_CERTIFICADO']
    template_name = 'certificados/entrega.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        evento = _obtener_evento_activo()
        hoy = date.today()
        contador_entregados_hoy = 0
        contador_total_entregados = 0
        evento_id = None
        if evento:
            evento_id = evento.id
            contador_total_entregados = Certificado.objects.filter(evento=evento).count()
            contador_entregados_hoy = Certificado.objects.filter(
                evento=evento,
                fecha_hora_entrega__date=hoy,
            ).count()
        ctx['evento_activo'] = evento
        ctx['contador_entregados_hoy'] = contador_entregados_hoy
        ctx['contador_total_entregados'] = contador_total_entregados
        ctx['evento_id'] = evento_id
        user = self.request.user
        ctx['nombre_operador'] = getattr(user, 'nombre_completo', user.username)
        return ctx


class ValidarTokenCertificadoJson(AjaxPermissionRequiredMixin, View):
    permission_required = 'certificados.add_certificado'
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
        
        # Intentar validar contra CertificadoProyecto primero (Certificados de Proyecto)
        try:
            token_uuid = uuid.UUID(token_limpio)
            from apps.certificados.models import CertificadoProyecto
            
            # Usamos filter().first() para evitar excepciones si la tabla no existe o el token no es UUID
            cp = CertificadoProyecto.objects.select_related(
                'proyecto__institucion',
                'proyecto__programa'
            ).filter(token_verificacion=token_uuid).first()
            
            if cp:
                return JsonResponse({
                    'status': 'OK',
                    'tipo_entidad': 'PROYECTO',
                    'persona': {
                        'nombre': cp.proyecto.nombre,
                        'rol_color': '#0067B1',
                        'rol_texto': 'PROYECTO',
                        'institucion': cp.proyecto.institucion.nombre if cp.proyecto.institucion else '',
                        'programa': cp.proyecto.programa.nombre if cp.proyecto.programa else '',
                        'proyecto': cp.proyecto.codigo,
                        'persona_id': cp.proyecto.id,
                    },
                    'evento_id': evento_id,
                }, status=200)
        except Exception:
            # Si falla (por tabla inexistente o error de UUID), continuamos a la lógica de Persona
            pass

        # Si no es proyecto, intentar validar contra Persona (Escarapelas)
        try:
            token_uuid = uuid.UUID(token_limpio)
        except (ValueError, AttributeError):
            return JsonResponse({
                'status': 'ROJO',
                'mensaje': 'QR inválido o no reconocido',
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


def _registrar_entrega_proyecto_logica(request, proyecto_id, evento_id, medio='QR'):
    from apps.certificados.models import CertificadoProyecto
    from django.utils import timezone
    operador = request.user
    
    try:
        cp = CertificadoProyecto.objects.select_related('proyecto', 'operador').get(
            proyecto_id=proyecto_id,
            evento_id=evento_id
        )
        
        if cp.estado == 'ENTREGADO':
            return {
                'status': 'AMARILLO',
                'mensaje': 'CERTIFICADO DE PROYECTO YA ENTREGADO',
                'fecha_hora': _formato_fecha_hora(cp.fecha_hora_entrega),
                'operador': cp.operador.nombre_completo if cp.operador else 'Sistema',
                'persona': {
                    'nombre': cp.proyecto.nombre,
                    'rol_color': '#0067B1',
                    'rol_texto': 'PROYECTO',
                },
                'codigo_unico': cp.codigo_unico,
            }
            
        cp.estado = 'ENTREGADO'
        cp.fecha_hora_entrega = timezone.now()
        cp.operador = operador
        cp.medio = medio
        cp.save()
        
        AuditoriaService.registrar(
            request=request,
            usuario=operador,
            accion='CERTIFICADO_PROYECTO',
            modulo='CERTIFICADOS',
            entidad='CertificadoProyecto',
            id_entidad=cp.pk,
            datos={
                'proyecto': cp.proyecto.nombre,
                'codigo': cp.proyecto.codigo,
                'medio': medio
            }
        )
        
        return {
            'status': 'VERDE',
            'mensaje': 'CERTIFICADO DE PROYECTO ENTREGADO',
            'fecha_hora': _formato_fecha_hora(cp.fecha_hora_entrega),
            'operador': operador.nombre_completo,
            'persona': {
                'nombre': cp.proyecto.nombre,
                'rol_color': '#0067B1',
                'rol_texto': 'PROYECTO',
            },
            'codigo_unico': cp.codigo_unico,
        }
    except Exception as e:
        return {
            'status': 'ROJO',
            'mensaje': f'Error al registrar entrega: {str(e)}',
        }


class RegistrarEntregaCertificadoJson(AjaxPermissionRequiredMixin, View):
    permission_required = 'certificados.add_certificado'
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

        # 1. Intentar como certificado de proyecto primero
        if token_raw:
            try:
                token_uuid = uuid.UUID(str(token_raw).strip())
                from apps.certificados.models import CertificadoProyecto
                cp = CertificadoProyecto.objects.filter(token_verificacion=token_uuid).first()
                if cp:
                    resultado = _registrar_entrega_proyecto_logica(request, cp.proyecto_id, int(evento_id), medio=medio)
                    return JsonResponse(resultado, status=200)
            except Exception:
                pass

        # 2. Lógica original para personas
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

        resultado = _registrar_certificado_logica(request, persona, int(evento_id), medio=medio)
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


class BuscarManualCertificadoView(RoleRequiredMixin, FormView):
    roles_requeridos = ['ADMINISTRADOR', 'OPERADOR_CERTIFICADO']
    template_name = 'certificados/buscar_manual.html'
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
                resultado_registro = _registrar_certificado_logica(
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


class GenerarCertificadosProyectosPdfView(RoleRequiredMixin, View):
    """Genera un PDF con certificados de proyectos (2 por hoja carta).
    Crea el registro CertificadoProyecto en BD si no existe (con su QR único)."""
    roles_requeridos = ['ADMINISTRADOR', 'OPERADOR_CERTIFICADO', 'REGISTRO']
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        from apps.proyectos.models import Proyecto
        from apps.core.simple_pdf import generar_certificados_proyectos_pdf
        from apps.certificados.models import CertificadoProyecto

        evento = _obtener_evento_activo()
        if not evento:
            return HttpResponse('No hay evento activo.', status=404)

        # Obtener proyectos activos del evento
        proyectos = list(Proyecto.objects.filter(
            evento=evento,
            estado__in=['INSCRITO', 'APROBADO'],
        ).select_related('institucion', 'programa', 'ficha').order_by('codigo'))

        # Crear el registro CertificadoProyecto para cada proyecto si no existe
        for proyecto in proyectos:
            CertificadoProyecto.objects.get_or_create(
                evento=evento,
                proyecto=proyecto,
            )

        buffer = generar_certificados_proyectos_pdf(proyectos, evento=evento)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="certificados_proyectos_{evento.id}.pdf"'
        return response
