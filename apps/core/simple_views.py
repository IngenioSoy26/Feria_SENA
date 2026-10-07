from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.urls import reverse

from apps.core.simple_pdf import (
    generar_escarapela_individual, generar_escarapelas_lote,
    generar_certificado_pdf, generar_certificados_lote, PLANTILLAS_CERTIFICADO,
)
from apps.core.mixins import RoleRequiredMixin
from apps.eventos.models import Evento, TipoIdentificacion, TipoServicio
from apps.instituciones.models import InstitucionEducativa
from apps.programas.models import ProgramaTecnico
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto, Aprendiz, Ficha
from apps.instructores.models import Instructor
from apps.invitados.models import Invitado
from apps.asistencia.models import AsistenciaEvento
from apps.refrigerios.models import EntregaServicio
from apps.certificados.models import Certificado


def _evento_activo():
    return Evento.objects.filter(activo=True, estado='ACTIVO').order_by('-fecha_inicio').first()


def _tipo_cc():
    t, _ = TipoIdentificacion.objects.get_or_create(codigo='CC', defaults={'nombre': 'Cédula de Ciudadanía', 'activo': True})
    return t


def _tipo_ti():
    t, _ = TipoIdentificacion.objects.get_or_create(codigo='TI', defaults={'nombre': 'Tarjeta de Identidad', 'activo': True})
    return t


def _tipo_ppt():
    t, _ = TipoIdentificacion.objects.get_or_create(codigo='PPT', defaults={'nombre': 'Permiso por Protección Temporal', 'activo': True})
    return t


TIPO_ID_MAP = {
    'CC': _tipo_cc,
    'TI': _tipo_ti,
    'PPT': _tipo_ppt,
}


def _obtener_tipo_id(codigo: str):
    fn = TIPO_ID_MAP.get((codigo or '').upper().strip())
    if fn:
        try:
            return fn()
        except Exception:
            return _tipo_cc()
    return _tipo_cc()


def _servicio_almuerzo(evento):
    s = TipoServicio.objects.filter(evento=evento, activo=True).order_by('orden').first()
    if not s:
        s, _ = TipoServicio.objects.get_or_create(evento=evento, nombre='Almuerzo', defaults={'orden': 1, 'activo': True})
    return s


def _es_admin(request):
    if not request.user or not request.user.is_authenticated:
        return False
    return request.user.is_superuser or request.user.groups.filter(name__in=['ADMINISTRADOR', 'REGISTRO']).exists()


def _operador_para_guardar(request):
    if request.user and request.user.is_authenticated and not request.user.is_anonymous:
        return request.user
    from apps.usuarios.models import Usuario
    from django.contrib.auth.models import Group
    try:
        usuario_publico, _ = Usuario.objects.get_or_create(
            username='operador_publico',
            defaults={
                'email': 'operador.publico@sena-feria.local',
                'nombres': 'Operador',
                'apellidos': 'Público (Token)',
                'rol_sistema': 'OPERADOR_ASISTENCIA',
                'activo': True,
            }
        )
        grupo, _ = Group.objects.get_or_create(name='OPERADOR_ASISTENCIA')
        if not usuario_publico.groups.filter(pk=grupo.pk).exists():
            usuario_publico.groups.add(grupo)
        return usuario_publico
    except Exception:
        return None


def _permitido(request, token_esperado):
    if _es_admin(request) or (request.user.is_authenticated and request.user.rol_sistema in ('ADMINISTRADOR', 'REGISTRO',
        'OPERADOR_ASISTENCIA', 'OPERADOR_REFRIGERIO', 'OPERADOR_CERTIFICADO', 'CONSULTA')):
        return True
    if token_esperado and request.resolver_match and request.resolver_match.kwargs:
        tok = request.resolver_match.kwargs.get('token_registro') or request.resolver_match.kwargs.get('token_operador') or ''
        if tok and token_esperado and tok == token_esperado:
            return True
    return False


def _solicitar_login_o_token(request, tipo='registro'):
    token_publico = settings.TOKEN_REGISTRO_PUBLICO if tipo == 'registro' else settings.TOKEN_OPERADORES_PUBLICO
    tok_kw = 'token_registro' if tipo == 'registro' else 'token_operador'
    header_nombre = 'X-Registro-Token' if tipo == 'registro' else 'X-Operador-Token'
    cookie_nombre = 'TOKEN_REGISTRO' if tipo == 'registro' else 'TOKEN_OPERADORES'
    ruta_kwargs = getattr(getattr(request, 'resolver_match', None), 'kwargs', None) or {}
    tok_recibido = (
        ruta_kwargs.get(tok_kw) or
        (request.headers.get(header_nombre) or '').strip() or
        (request.COOKIES.get(cookie_nombre) or '').strip() or
        (request.GET.get('token') or '').strip() or
        ''
    )
    if tok_recibido:
        if token_publico and tok_recibido == token_publico:
            return None
        return HttpResponse('Enlace no autorizado o caducado. Verifica con el administrador el enlace correcto.', status=403)
    if request.user.is_authenticated:
        return None
    return HttpResponseRedirect(reverse('login') + '?next=' + request.path)


# ============================================================
# PANTALLA DE INICIO / HOME SIMPLIFICADA
# ============================================================
class HomeSimpleView(LoginRequiredMixin, View):
    def get(self, request, **_):
        evento = _evento_activo()
        es_admin = _es_admin(request)
        base = request.build_absolute_uri('/').rstrip('/')
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        t_o = settings.TOKEN_OPERADORES_PUBLICO or ''
        enlaces = {
            'registro': f"{base}/r/{t_r}/registro/" if t_r else None,
            'op_asistencia': f"{base}/o/{t_o}/asistencia/" if t_o else None,
            'op_refrigerios': f"{base}/o/{t_o}/refrigerios/" if t_o else None,
            'op_certificados': f"{base}/o/{t_o}/certificados/" if t_o else None,
        }
        return render(request, 'simple/home.html', {
            'evento': evento,
            'es_admin': es_admin,
            'enlaces_publicos': enlaces,
        })


# ============================================================
# PANEL ADMINISTRATIVO UNIFICADO (Configuración y maestra de datos)
# ============================================================
class PanelAdminDashboardView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get(self, request, **_ignorado):
        admin_prefix = getattr(settings, 'DJANGO_ADMIN_URL', 'admin/').strip('/')
        admin_root = f'/{admin_prefix}/'

        c = {}
        c['eventos'] = Evento.objects.count()
        c['eventos_activos'] = Evento.objects.filter(activo=True, estado='ACTIVO').count()
        c['instituciones'] = InstitucionEducativa.objects.count()
        c['instituciones_activas'] = InstitucionEducativa.objects.filter(activo=True).count()
        c['programas'] = ProgramaTecnico.objects.count()
        c['programas_activos'] = ProgramaTecnico.objects.filter(activo=True).count()
        c['instructores'] = Instructor.objects.count()
        c['fichas'] = Ficha.objects.count()
        c['fichas_activas'] = Ficha.objects.filter(activo=True).count()
        c['proyectos'] = Proyecto.objects.count()
        c['proyectos_aprobados'] = Proyecto.objects.filter(estado='APROBADO').count()
        c['personas'] = Persona.objects.count()
        c['aprendices'] = Aprendiz.objects.count()
        c['asistencias'] = 0
        c['refrigerios'] = 0
        c['certificados'] = 0
        try:
            ev = _evento_activo()
            if ev:
                c['asistencias'] = AsistenciaEvento.objects.filter(evento=ev).count()
                svc = _servicio_almuerzo(ev)
                c['refrigerios'] = EntregaServicio.objects.filter(evento=ev, tipo_servicio=svc).count()
                c['certificados'] = Certificado.objects.filter(evento=ev).count()
        except Exception:
            pass

        evento = _evento_activo()
        base = request.build_absolute_uri('/').rstrip('/')
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        t_o = settings.TOKEN_OPERADORES_PUBLICO or ''
        enlaces = {
            'registro': f"{base}/r/{t_r}/registro/" if t_r else None,
            'op_asistencia': f"{base}/o/{t_o}/asistencia/" if t_o else None,
            'op_refrigerios': f"{base}/o/{t_o}/refrigerios/" if t_o else None,
            'op_certificados': f"{base}/o/{t_o}/certificados/" if t_o else None,
        }
        return render(request, 'simple/panel_admin.html', {
            'counts': c,
            'admin_root': admin_root,
            'evento': evento,
            'enlaces_publicos': enlaces,
            't_r': t_r,
            't_o': t_o,
        })


# ============================================================
# FORMULARIO DE REGISTRO ÚNICO (PROYECTO + APRENDICES DINÁMICOS)
# ============================================================
class WizardRegistroView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    modo = 'registro'

    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, paso=1, **_ignorado):
        evento = _evento_activo()
        fichas_activas = list(
            Ficha.objects.filter(activo=True).select_related(
                'institucion', 'programa', 'instructor_lider', 'instructor_lider__persona'
            ).order_by('numero')
        )
        return render(request, 'simple/wizard_registro.html', {
            'evento': evento,
            'municipios': sorted(set(
                list(InstitucionEducativa.objects.exclude(municipio='').values_list('municipio', flat=True))
                + ['Riohacha', 'Maicao', 'Uribia', 'Manaure', 'Albania', 'Dibulla', 'San Juan del Cesar', 'Fonseca', 'Barrancas', 'Hatonuevo']
            )),
            'tipos_identificacion': ['CC', 'TI', 'PPT'],
            'max_aprendices': settings.MAX_APRENDICES_POR_PROYECTO,
            'fichas_activas': fichas_activas,
        })

    @transaction.atomic
    def post(self, request, paso=1, **_ignorado):
        evento = _evento_activo()
        if not evento:
            messages.error(request, 'No hay un evento ACTIVO. Crea primero un evento desde Administración.')
            return redirect('simple:wizard')

        try:
            import re
            max_ap = settings.MAX_APRENDICES_POR_PROYECTO

            # ---- DATOS DEL PROYECTO / FICHA ----
            nombre_ie = request.POST.get('nombre_ie', '').strip()
            municipio_ie = request.POST.get('municipio_ie', '').strip() or 'Riohacha'
            nombre_programa = request.POST.get('nombre_programa', '').strip()
            nombre_proyecto = request.POST.get('nombre_proyecto', '').strip()
            codigo_ficha_raw = request.POST.get('codigo_ficha', request.POST.get('codigo_proyecto', '') or '').strip()
            codigo_ficha = re.sub(r'\D', '', codigo_ficha_raw)
            nombre_instructor = request.POST.get('instructor_nombre', '').strip()
            cedula_instructor = request.POST.get('instructor_cedula', '').strip()

            if not nombre_ie or not nombre_programa or not nombre_proyecto:
                messages.error(request, '⚠ Faltan datos obligatorios: Institución, Programa y Nombre del proyecto.')
                return redirect('simple:wizard')

            if not codigo_ficha:
                messages.error(request, '⚠ El Código de Ficha es obligatorio. Debe tener 7 dígitos numéricos.')
                return redirect('simple:wizard')
            if len(codigo_ficha) != 7 or not re.fullmatch(r'\d{7}', codigo_ficha):
                messages.error(request, f'⚠ El Código de Ficha debe tener EXACTAMENTE 7 dígitos numéricos. Tienes {len(codigo_ficha)} ("{codigo_ficha}").')
                return redirect('simple:wizard')

            # ---- INSTITUCIÓN + PROGRAMA (deduplicados iexact) ----
            codigo_ie = 'INS-' + codigo_ficha
            colegio = InstitucionEducativa.objects.filter(nombre__iexact=nombre_ie).order_by('id').first()
            if not colegio:
                colegio, _ = InstitucionEducativa.objects.get_or_create(
                    nombre=nombre_ie,
                    defaults={'codigo': codigo_ie, 'municipio': municipio_ie},
                )
            if municipio_ie and colegio.municipio != municipio_ie:
                colegio.municipio = municipio_ie
                colegio.save(update_fields=['municipio'])
            if not colegio.codigo:
                colegio.codigo = codigo_ie
                colegio.save(update_fields=['codigo'])

            codigo_prog = 'PROG-' + codigo_ficha
            programa = ProgramaTecnico.objects.filter(nombre__iexact=nombre_programa).order_by('id').first()
            if not programa:
                programa, _ = ProgramaTecnico.objects.get_or_create(
                    nombre=nombre_programa,
                    defaults={'codigo': codigo_prog},
                )
            if not programa.codigo:
                programa.codigo = codigo_prog
                programa.save(update_fields=['codigo'])

            # ---- INSTRUCTOR LÍDER (opcional) ----
            instructor_obj = None
            if nombre_instructor:
                cedula_ins = cedula_instructor or str(90000000 + Instructor.objects.count() + 1)
                nombres_ins, apellidos_ins = self._separar_nombres_apellidos(nombre_instructor)
                p_ins, _ = Persona.objects.get_or_create(
                    tipo_identificacion=_tipo_cc(),
                    numero_identificacion=cedula_ins,
                    defaults={
                        'nombres': nombres_ins, 'apellidos': apellidos_ins,
                        'correo': f"instructor_{cedula_ins}@sena.edu.co",
                        'tipo_persona': 'INSTRUCTOR',
                    },
                )
                instructor_obj, _ = Instructor.objects.get_or_create(persona=p_ins)
                if not instructor_obj.programas.filter(pk=programa.pk).exists():
                    instructor_obj.programas.add(programa)

            # ---- FICHA MAESTRA (si existe, autocompletar desde el catálogo) ----
            ficha_obj = Ficha.objects.filter(numero=codigo_ficha, activo=True).first()
            if ficha_obj:
                if ficha_obj.institucion_id and not nombre_ie:
                    nombre_ie = ficha_obj.institucion.nombre
                    colegio = ficha_obj.institucion
                if ficha_obj.municipio and not municipio_ie:
                    municipio_ie = ficha_obj.municipio
                if ficha_obj.programa_id and not nombre_programa:
                    nombre_programa = ficha_obj.programa.nombre
                    programa = ficha_obj.programa
                if ficha_obj.instructor_lider_id and not nombre_instructor:
                    p_lider = getattr(ficha_obj.instructor_lider, 'persona', None)
                    if p_lider:
                        nombre_instructor = p_lider.nombre_completo
                        cedula_instructor = p_lider.numero_identificacion
                        instructor_obj = ficha_obj.instructor_lider

            # ---- PROYECTO (Ficha) ----
            proyecto_defaults = {
                'nombre': nombre_proyecto,
                'descripcion': f'{nombre_proyecto} - {colegio.nombre}',
                'institucion': colegio,
                'programa': programa,
                'instructor_responsable': instructor_obj,
                'estado': 'APROBADO',
            }
            if ficha_obj:
                proyecto_defaults['ficha'] = ficha_obj
            proyecto, creado = Proyecto.objects.get_or_create(
                evento=evento,
                codigo=codigo_ficha,
                defaults=proyecto_defaults,
            )
            if not creado:
                proyecto.nombre = nombre_proyecto
                proyecto.institucion = colegio
                proyecto.programa = programa
                if instructor_obj:
                    proyecto.instructor_responsable = instructor_obj
                if ficha_obj:
                    proyecto.ficha = ficha_obj
                proyecto.descripcion = f'{nombre_proyecto} - {colegio.nombre}'
                save_fields = ['nombre', 'descripcion', 'institucion', 'programa', 'instructor_responsable']
                if ficha_obj:
                    save_fields.append('ficha')
                proyecto.save(update_fields=save_fields)
                messages.warning(request, f'ℹ Ficha #{codigo_ficha} ya existía. Se actualizaron sus datos.')

            # ---- APRENDICES (SUB-FORMULARIO DINÁMICO, arreglos) ----
            tipos = request.POST.getlist('apr_tipo_doc[]') or request.POST.getlist('apr_tipo_doc') or []
            nums = request.POST.getlist('apr_num_doc[]') or request.POST.getlist('apr_num_doc') or []
            noms = request.POST.getlist('apr_nombre[]') or request.POST.getlist('apr_nombre') or []
            tels = request.POST.getlist('apr_telefono[]') or request.POST.getlist('apr_telefono') or []

            n = max(len(tipos), len(nums), len(noms), len(tels))
            tuplas = []
            for i in range(n):
                t = (tipos[i] if i < len(tipos) else '').strip() or 'CC'
                nd = re.sub(r'\D', '', (nums[i] if i < len(nums) else '') or '')
                nm = (noms[i] if i < len(noms) else '').strip()
                tl = re.sub(r'\D', '', (tels[i] if i < len(tels) else '') or '')
                if not nd or not nm:
                    continue  # skip filas vacías
                tuplas.append((t, nd, nm, tl))

            # Capo MAX por configuración
            if len(tuplas) > max_ap:
                messages.warning(request, f'⚠ Máximo permitido {max_ap} aprendices por ficha. Se guardaron sólo los primeros {max_ap}.')
                tuplas = tuplas[:max_ap]

            if len(tuplas) == 0:
                messages.warning(request, 'ℹ No se incluyeron aprendices. Puedes agregarlos después editando la ficha.')

            aprendices_guardados = 0
            for t, nd, nm, tl in tuplas:
                nombres_a, apellidos_a = self._separar_nombres_apellidos(nm)
                persona_a, _ = Persona.objects.get_or_create(
                    tipo_identificacion=_obtener_tipo_id(t),
                    numero_identificacion=nd,
                    defaults={
                        'nombres': nombres_a,
                        'apellidos': apellidos_a,
                        'telefono': tl or None,
                        'tipo_persona': 'APRENDIZ',
                    },
                )
                # Actualizar teléfono si cambió
                if tl and persona_a.telefono != tl:
                    persona_a.telefono = tl
                    persona_a.save(update_fields=['telefono'])
                Aprendiz.objects.get_or_create(persona=persona_a, defaults={'proyecto': proyecto, 'grado': '11'})
                aprendices_guardados += 1

            messages.success(
                request,
                f'✔ Ficha #{codigo_ficha} guardada OK · Proyecto: "{proyecto.nombre}" · {aprendices_guardados} aprendiz(es) · {colegio.nombre} ({colegio.municipio}).'
            )
            return redirect('simple:home')

        except Exception as e:
            messages.error(request, f'⚠ Hubo un error al guardar: {e}')
            return redirect('simple:wizard')

    @staticmethod
    def _separar_nombres_apellidos(texto):
        import re
        texto = (texto or '').strip()
        if not texto:
            return 'Sin', 'Nombre'
        partes = re.split(r'\s+', texto)
        if len(partes) == 1:
            return partes[0], 'S.A.'
        if len(partes) == 2:
            return partes[0], partes[1]
        if len(partes) == 3:
            return partes[0], ' '.join(partes[1:])
        return ' '.join(partes[:2]), ' '.join(partes[2:])


# ============================================================
# AUTOCOMPLETADO - BÚSQUEDA RÁPIDA (Instituciones, Programas, Instructores por AJAX)
# ============================================================
class BuscarAjaxView(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return JsonResponse({'ok': False, 'mensaje': 'Autenticación requerida'})
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        tipo = request.GET.get('tipo', '')
        q = request.GET.get('q', '').strip()
        if tipo == 'institucion':
            data = list(
                InstitucionEducativa.objects.filter(nombre__icontains=q).order_by('nombre')[:15].values('id', 'nombre', 'municipio')
            )
        elif tipo == 'programa':
            data = list(
                ProgramaTecnico.objects.filter(nombre__icontains=q).order_by('nombre')[:15].values('id', 'nombre')
            )
        elif tipo == 'instructor':
            data = list(
                Instructor.objects.select_related('persona').filter(
                    persona__nombres__icontains=q
                ) | Instructor.objects.select_related('persona').filter(
                    persona__apellidos__icontains=q
                ).order_by('persona__apellidos')[:15]
            )
            data = [{'id': i.pk, 'nombre': i.persona.get_full_name(), 'cedula': i.persona.numero_identificacion} for i in data]
        else:
            data = []
        return JsonResponse({'ok': True, 'data': data})


# ============================================================
# PANTALLAS MÓVILES OPERADOR (ASISTENCIA / REFRIGERIOS / CERTIFICADOS)
# ============================================================
class OperadorMobileView(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'operadores')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, tipo='asistencia', **_ignorado):
        evento = _evento_activo()
        total = 0
        ingresaron = 0
        faltan = 0
        porcentaje = 0
        if evento:
            try:
                from django.db.models import Q
                qs = Persona.objects.filter(
                    Q(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']),
                    activo=True,
                )
                total = qs.count()
                if tipo == 'asistencia':
                    ids = set(AsistenciaEvento.objects.filter(evento=evento).values_list('persona_id', flat=True))
                    ingresaron = len(ids)
                elif tipo == 'refrigerios':
                    svc = _servicio_almuerzo(evento)
                    if svc:
                        ids = set(EntregaServicio.objects.filter(evento=evento, tipo_servicio=svc).values_list('persona_id', flat=True))
                        ingresaron = len(ids)
                elif tipo == 'certificados':
                    ids = set(Certificado.objects.filter(evento=evento).values_list('persona_id', flat=True))
                    ingresaron = len(ids)
                faltan = max(total - ingresaron, 0)
                porcentaje = round((ingresaron / total) * 100, 1) if total > 0 else 0
            except Exception:
                pass
        tok_pub = getattr(settings, 'TOKEN_OPERADORES_PUBLICO', '') or ''
        return render(request, 'simple/operador_mobile.html', {
            'tipo': tipo,
            'evento': evento,
            'servicio': _servicio_almuerzo(evento) if tipo == 'refrigerios' else None,
            'stats_iniciales': {
                'total': total, 'ingresaron': ingresaron, 'faltan': faltan, 'porcentaje': porcentaje,
            },
            'token_operadores_publico': tok_pub,
        })


# ============================================================
# STATS EN VIVO — Polling Panel Operador Móvil (2 tarjetas)
#   Parámetro URL: ?tipo=asistencia|refrigerios|certificados
# ============================================================
class StatsOperadorAjax(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'operadores')
        if resp is not None:
            return JsonResponse({'ok': False, 'total': 0, 'ingresaron': 0, 'faltan': 0, 'ts': None})
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        tipo = (request.GET.get('tipo') or 'asistencia').strip().lower()
        evento = _evento_activo()
        if not evento:
            return JsonResponse({'ok': False, 'tipo': tipo, 'total': 0, 'ingresaron': 0, 'faltan': 0, 'porcentaje': 0, 'ts': None})
        try:
            from django.db.models import Q
            qs_personas_feria = Persona.objects.filter(
                Q(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']),
                activo=True,
            )
            total = qs_personas_feria.count()
            if tipo == 'asistencia':
                ids_ingresados = set(AsistenciaEvento.objects.filter(evento=evento).values_list('persona_id', flat=True))
                ingresaron = len(ids_ingresados)
            elif tipo == 'refrigerios':
                svc = _servicio_almuerzo(evento)
                if svc:
                    ids_ingresados = set(EntregaServicio.objects.filter(evento=evento, tipo_servicio=svc).values_list('persona_id', flat=True))
                    ingresaron = len(ids_ingresados)
                else:
                    ingresaron = 0
            elif tipo == 'certificados':
                ids_ingresados = set(Certificado.objects.filter(evento=evento).values_list('persona_id', flat=True))
                ingresaron = len(ids_ingresados)
            else:
                ids_ingresados = set(AsistenciaEvento.objects.filter(evento=evento).values_list('persona_id', flat=True))
                ingresaron = len(ids_ingresados)
            faltan = max(total - ingresaron, 0)
            porcentaje = round((ingresaron / total) * 100, 1) if total > 0 else 0
            from datetime import datetime
            return JsonResponse({
                'ok': True, 'tipo': tipo, 'evento_id': evento.id,
                'total': total, 'ingresaron': ingresaron, 'faltan': faltan,
                'porcentaje': porcentaje, 'ts': datetime.now().strftime('%H:%M:%S'),
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e), 'total': 0, 'ingresaron': 0, 'faltan': 0, 'porcentaje': 0, 'ts': None})


# ============================================================
# STATS EN VIVO — Polling Panel Admin (Ingresados vs Faltan)
# ============================================================
class StatsOperativosAjax(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get(self, request, **_ignorado):
        evento = _evento_activo()
        if not evento:
            return JsonResponse({
                'ok': False, 'evento': None,
                'total_personas': 0, 'ingresaron': 0, 'faltan': 0,
                'refrigerios': 0, 'certificados': 0, 'porcentaje': 0, 'ts': None,
            })
        try:
            from django.db.models import Q
            qs_personas_feria = Persona.objects.filter(
                Q(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']),
                activo=True,
            )
            total = qs_personas_feria.count()
            ids_ingresados = set(
                AsistenciaEvento.objects.filter(evento=evento)
                .values_list('persona_id', flat=True)
            )
            ingresaron = len(ids_ingresados)
            faltan = max(total - ingresaron, 0)
            svc = _servicio_almuerzo(evento)
            refrigerios = EntregaServicio.objects.filter(evento=evento, tipo_servicio=svc).count() if svc else 0
            certificados = Certificado.objects.filter(evento=evento).count()
            porcentaje = round((ingresaron / total) * 100, 1) if total > 0 else 0
            from datetime import datetime
            return JsonResponse({
                'ok': True,
                'evento': {'id': evento.id, 'nombre': evento.nombre, 'municipio': evento.municipio or ''},
                'total_personas': total, 'ingresaron': ingresaron, 'faltan': faltan,
                'refrigerios': refrigerios, 'certificados': certificados,
                'porcentaje': porcentaje,
                'ts': datetime.now().strftime('%H:%M:%S'),
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})


class RegistrarOperadorAjax(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'operadores')
        if resp is not None:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'Autenticación requerida.'})
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, **_ignorado):
        try:
            import json
            body = json.loads(request.body or '{}')
        except Exception:
            body = request.POST.dict()
        token = (body.get('token') or body.get('qr_token') or '').strip()
        medio = body.get('medio') or 'QR'
        tipo = body.get('tipo') or 'asistencia'
        evento = _evento_activo()

        if not evento:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'No hay evento activo.'})
        if not token:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'Código QR inválido.'})

        persona = Persona.objects.filter(qr_token=token).first()
        if not persona:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'Código QR no registrado en el sistema.'})

        label = persona.get_full_name()
        extra = ''
        tipo_asistente = 'Persona'
        nombre_proyecto = ''
        ficha_codigo = ''
        try:
            if persona.tipo_persona == 'APRENDIZ':
                tipo_asistente = 'Aprendiz Con Proyecto'
                if hasattr(persona, 'perfil_aprendiz') and persona.perfil_aprendiz:
                    nombre_proyecto = persona.perfil_aprendiz.proyecto.nombre if persona.perfil_aprendiz.proyecto else ''
                    ficha_codigo = persona.perfil_aprendiz.proyecto.ficha.numero if (persona.perfil_aprendiz.proyecto and persona.perfil_aprendiz.proyecto.ficha) else ''
                    extra = ' · Proyecto: ' + (nombre_proyecto or 'Sin asignar')
                    if ficha_codigo:
                        extra += ' · Ficha: ' + ficha_codigo
            elif persona.tipo_persona == 'INSTRUCTOR':
                tipo_asistente = 'Instructor'
                extra = ' · Instructor SENA'
            elif persona.tipo_persona == 'INVITADO':
                tipo_asistente = 'Invitado Especial'
                extra = ' · Invitado a la feria'
        except Exception:
            pass
        tipo_doc = persona.tipo_identificacion.abreviatura if persona.tipo_identificacion else 'CC'
        numero_doc = persona.numero_identificacion or ''

        operador = _operador_para_guardar(request)
        if not operador:
            return JsonResponse({
                'ok': False, 'status': 'ROJO',
                'mensaje': 'No se pudo determinar el operador. Inicia sesión o usa el enlace token correcto.',
            })

        try:
            if tipo == 'asistencia':
                _, created = AsistenciaEvento.objects.get_or_create(
                    evento=evento, persona=persona,
                    defaults={'operador': operador, 'medio': medio},
                )
                status = 'VERDE' if created else 'AMARILLO'
                mensaje = 'Ingreso registrado ✔' if created else '⚠ Ya había ingresado antes'
            elif tipo == 'refrigerios':
                svc = _servicio_almuerzo(evento)
                _, created = EntregaServicio.objects.get_or_create(
                    evento=evento, persona=persona, tipo_servicio=svc,
                    defaults={'operador': operador, 'medio': medio},
                )
                status = 'VERDE' if created else 'AMARILLO'
                mensaje = f'{svc.nombre} entregado ✔' if created else '⚠ Ya se le había entregado'
            elif tipo == 'certificados':
                obj, created = Certificado.objects.get_or_create(
                    evento=evento, persona=persona,
                    defaults={'operador': operador, 'medio': medio},
                )
                if not obj.codigo_unico:
                    obj.save()
                status = 'VERDE'
                mensaje = 'Certificado entregado ✔ Código: ' + obj.codigo_unico
            else:
                return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'Tipo desconocido.'})
        except Exception as e:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': f'Error: {e}'})

        nombre_ie = ''
        municipio_persona = ''
        correo = persona.correo or ''
        telefono = persona.telefono or ''
        direccion = persona.direccion or ''
        genero = ''
        if persona.genero:
            genero = {'M': 'Masculino', 'F': 'Femenino', 'O': 'Otro'}.get(persona.genero, '')
        if persona.tipo_persona == 'APRENDIZ':
            try:
                if hasattr(persona, 'perfil_aprendiz') and persona.perfil_aprendiz and persona.perfil_aprendiz.proyecto:
                    proy = persona.perfil_aprendiz.proyecto
                    if proy.institucion:
                        nombre_ie = proy.institucion.nombre or ''
                        if proy.institucion.municipio:
                            municipio_persona = proy.institucion.municipio
                    if proy.ficha and proy.ficha.numero and not ficha_codigo:
                        ficha_codigo = proy.ficha.numero
            except Exception:
                pass
        elif persona.tipo_persona == 'INSTRUCTOR':
            try:
                if hasattr(persona, 'perfil_instructor') and persona.perfil_instructor:
                    if persona.perfil_instructor.municipio:
                        municipio_persona = persona.perfil_instructor.municipio
            except Exception:
                pass
        elif persona.tipo_persona == 'INVITADO':
            try:
                if hasattr(persona, 'perfil_invitado') and persona.perfil_invitado:
                    if persona.perfil_invitado.institucion_procedencia:
                        nombre_ie = persona.perfil_invitado.institucion_procedencia
                    if persona.perfil_invitado.municipio:
                        municipio_persona = persona.perfil_invitado.municipio
            except Exception:
                pass

        return JsonResponse({
            'ok': True,
            'status': status,
            'mensaje': mensaje,
            'nombre': label,
            'rol': (persona.tipo_persona or '').title(),
            'extra': extra,
            'tipo_asistente': tipo_asistente,
            'tipo_documento': tipo_doc,
            'numero_documento': numero_doc,
            'nombre_proyecto': nombre_proyecto,
            'codigo_ficha': ficha_codigo,
            'institucion': nombre_ie,
            'municipio': municipio_persona or (evento.municipio if evento else ''),
            'correo': correo,
            'telefono': telefono,
            'direccion': direccion,
            'genero': genero,
            'es_duplicado': (status == 'AMARILLO'),
            'es_nuevo': (status == 'VERDE'),
        })


# ============================================================
# DASHBOARD SIMPLIFICADO - 3 KPIs + 3 GRÁFICOS
# ============================================================
class DashboardSimpleView(LoginRequiredMixin, View):
    def get(self, request, **_ignorado):
        evento = _evento_activo()
        if not evento:
            return render(request, 'simple/dashboard.html', {'evento': None})
        total_personas = Persona.objects.count()
        total_aprendices = Persona.objects.filter(tipo_persona='APRENDIZ').count()
        total_instructores = Persona.objects.filter(tipo_persona='INSTRUCTOR').count()
        total_invitados = Persona.objects.filter(tipo_persona='INVITADO').count()
        total_proyectos = Proyecto.objects.filter(evento=evento).count()
        total_colegios = InstitucionEducativa.objects.count()

        asistentes = AsistenciaEvento.objects.filter(evento=evento).count()
        ausentes = max(total_personas - asistentes, 0)

        servicio = _servicio_almuerzo(evento)
        refrigerios_entregados = EntregaServicio.objects.filter(evento=evento, tipo_servicio=servicio).count() if servicio else 0
        refrigerios_pendientes = max(asistentes - refrigerios_entregados, 0)

        certificados_entregados = Certificado.objects.filter(evento=evento).count()
        certificados_pendientes = max(asistentes - certificados_entregados, 0)

        return render(request, 'simple/dashboard.html', {
            'evento': evento,
            'total_personas': total_personas,
            'total_aprendices': total_aprendices,
            'total_instructores': total_instructores,
            'total_invitados': total_invitados,
            'total_proyectos': total_proyectos,
            'total_colegios': total_colegios,
            'asistentes': asistentes,
            'ausentes': ausentes,
            'refrigerios_entregados': refrigerios_entregados,
            'refrigerios_pendientes': refrigerios_pendientes,
            'certificados_entregados': certificados_entregados,
            'certificados_pendientes': certificados_pendientes,
        })


# ============================================================
# LISTADOS: COLEGIOS, PROGRAMAS, INSTRUCTORES, INVITADOS (ÚNICOS, SIN REPETICIONES)
# ============================================================
class ListadoUnicosView(LoginRequiredMixin, View):
    def get(self, request, que='colegios', **_ignorado):
        data = None
        titulo = ''
        if que == 'colegios':
            titulo = 'Instituciones Educativas (únicas)'
            data = InstitucionEducativa.objects.order_by('nombre').all()
        elif que == 'programas':
            titulo = 'Programas Técnicos (únicos)'
            data = ProgramaTecnico.objects.order_by('nombre').all()
        elif que == 'instructores':
            titulo = 'Instructores (únicos)'
            data = Instructor.objects.select_related('persona').order_by('persona__apellidos').all()
        elif que == 'invitados':
            titulo = 'Invitados (únicos)'
            data = Invitado.objects.select_related('persona').order_by('persona__apellidos').all()
        elif que == 'proyectos':
            titulo = 'Proyectos registrados'
            data = Proyecto.objects.select_related('institucion', 'programa', 'instructor_responsable__persona').order_by('codigo').all()
        elif que == 'aprendices':
            titulo = 'Aprendices por proyecto'
            data = Aprendiz.objects.select_related('persona', 'proyecto').order_by('proyecto__codigo').all()
        return render(request, 'simple/listados_unicos.html', {
            'que': que, 'titulo': titulo, 'filas': data,
        })


# ============================================================
# ESCARAPELAS PDF - Individual / Lotes
# ============================================================
class DescargarEscarapelaIndividual(LoginRequiredMixin, View):
    def get(self, request, persona_id, **_ignorado):
        p = get_object_or_404(Persona, pk=persona_id)
        evento = _evento_activo()
        proyecto = None
        try:
            if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz:
                proyecto = p.perfil_aprendiz.proyecto
        except Exception:
            pass
        buffer = generar_escarapela_individual(p, evento=evento, proyecto=proyecto)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="escarapela_{p.numero_identificacion or p.id}.pdf"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


class DescargarEscarapelasLote(LoginRequiredMixin, View):
    def get(self, request, grupo='todos', **_ignorado):
        evento = _evento_activo()
        queryset = Persona.objects.filter(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO'])
        items = []
        if grupo == 'todos':
            for p in queryset.order_by('tipo_persona', 'apellidos'):
                proy = None
                try:
                    if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz:
                        proy = p.perfil_aprendiz.proyecto
                except Exception:
                    pass
                items.append((p, proy))
        elif grupo == 'aprendices':
            for a in Aprendiz.objects.select_related('persona', 'proyecto').order_by('persona__apellidos').all():
                items.append((a.persona, a.proyecto))
        elif grupo == 'instructores':
            for i in Instructor.objects.select_related('persona').order_by('persona__apellidos').all():
                items.append((i.persona, None))
        elif grupo == 'invitados':
            for i in Invitado.objects.select_related('persona').order_by('persona__apellidos').all():
                items.append((i.persona, None))
        elif grupo == 'asistentes':
            asistencias = AsistenciaEvento.objects.filter(evento=evento).select_related('persona')
            seen = set()
            for a in asistencias:
                if a.persona_id in seen:
                    continue
                seen.add(a.persona_id)
                proy = None
                try:
                    if hasattr(a.persona, 'perfil_aprendiz') and a.persona.perfil_aprendiz:
                        proy = a.persona.perfil_aprendiz.proyecto
                except Exception:
                    pass
                items.append((a.persona, proy))
        else:
            try:
                pk = int(grupo)
                institucion = get_object_or_404(InstitucionEducativa, pk=pk)
                for proyecto in Proyecto.objects.filter(institucion=institucion).order_by('codigo'):
                    for a in Aprendiz.objects.filter(proyecto=proyecto).select_related('persona'):
                        items.append((a.persona, proyecto))
                    if proyecto.instructor_responsable and proyecto.instructor_responsable.persona:
                        items.append((proyecto.instructor_responsable.persona, proyecto))
                grupo = f'institucion_{pk}'
            except Exception:
                pass

        if not items:
            messages.warning(request, 'No hay personas para generar escarapelas en este grupo.')
            return redirect('simple:listados', que='aprendices')

        buffer = generar_escarapelas_lote(items, evento=evento, nombre_archivo=f'escarapelas_{grupo}.pdf')
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="escarapelas_{grupo}.pdf"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


# ============================================================
# CERTIFICADOS - Formulario de EDICIÓN (previa) y Descarga
# ============================================================
class EditarCertificadoView(LoginRequiredMixin, View):
    def get(self, request, persona_id, tipo='ASISTENCIA', **_ignorado):
        p = get_object_or_404(Persona, pk=persona_id)
        tipo = (tipo or 'ASISTENCIA').upper()
        evento = _evento_activo()
        proyecto = None
        try:
            if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz and p.perfil_aprendiz.proyecto:
                proyecto = p.perfil_aprendiz.proyecto
        except Exception:
            pass
        from datetime import date
        from apps.core.simple_pdf import _reemplazar_plantilla
        plantilla = PLANTILLAS_CERTIFICADO.get(tipo, PLANTILLAS_CERTIFICADO['ASISTENCIA'])
        vars_ = _reemplazar_plantilla(plantilla, p, evento=evento, proyecto=proyecto)
        return render(request, 'simple/editar_certificado.html', {
            'persona': p,
            'tipo': tipo,
            'plantilla': plantilla,
            'vars_': vars_,
            'evento': evento,
            'proyecto': proyecto,
            'fecha_hoy': date.today().strftime('%Y-%m-%d'),
        })

    def post(self, request, persona_id, tipo='ASISTENCIA', **_ignorado):
        p = get_object_or_404(Persona, pk=persona_id)
        tipo = (tipo or 'ASISTENCIA').upper()
        evento = _evento_activo()
        proyecto = None
        try:
            if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz and p.perfil_aprendiz.proyecto:
                proyecto = p.perfil_aprendiz.proyecto
        except Exception:
            pass
        overrides = {
            'NOMBRE_COMPLETO': request.POST.get('NOMBRE_COMPLETO') or None,
            'TIPO_ID': request.POST.get('TIPO_ID') or None,
            'NUMERO_ID': request.POST.get('NUMERO_ID') or None,
            'EVENTO': request.POST.get('EVENTO') or None,
            'LUGAR': request.POST.get('LUGAR') or None,
            'MUNICIPIO': request.POST.get('MUNICIPIO') or None,
            'FECHA_INICIO': request.POST.get('FECHA_INICIO') or None,
            'FECHA_FIN': request.POST.get('FECHA_FIN') or None,
            'FECHA_EMISION': request.POST.get('FECHA_EMISION') or None,
            'ROL': request.POST.get('ROL') or None,
            'NOMBRE_PROYECTO': request.POST.get('NOMBRE_PROYECTO') or None,
            'CODIGO_PROYECTO': request.POST.get('CODIGO_PROYECTO') or None,
            'INSTITUCION': request.POST.get('INSTITUCION') or None,
            'FIRMA_1_NOMBRE': request.POST.get('FIRMA_1_NOMBRE') or None,
            'FIRMA_1_CARGO': request.POST.get('FIRMA_1_CARGO') or None,
            'FIRMA_2_NOMBRE': request.POST.get('FIRMA_2_NOMBRE') or None,
            'FIRMA_2_CARGO': request.POST.get('FIRMA_2_CARGO') or None,
        }
        overrides = {k: v for k, v in overrides.items() if v}

        modo = request.POST.get('accion', 'descargar')
        buffer = generar_certificado_pdf(p, tipo=tipo, evento=evento, proyecto=proyecto, overrides=overrides)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f'{tipo}_{p.numero_identificacion or p.id}.pdf'
        if modo == 'previsualizar':
            resp['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


class DescargarCertificadosLoteView(LoginRequiredMixin, View):
    def get(self, request, tipo='ASISTENCIA', grupo='asistentes', **_ignorado):
        evento = _evento_activo()
        tipo = (tipo or 'ASISTENCIA').upper()
        lista = []
        if grupo == 'asistentes' and evento:
            asistencias = AsistenciaEvento.objects.filter(evento=evento).select_related('persona')
            seen = set()
            for a in asistencias:
                if a.persona_id in seen:
                    continue
                seen.add(a.persona_id)
                proy = None
                try:
                    if hasattr(a.persona, 'perfil_aprendiz') and a.persona.perfil_aprendiz:
                        proy = a.persona.perfil_aprendiz.proyecto
                except Exception:
                    pass
                lista.append((a.persona, proy))
        elif grupo == 'todos':
            for p in Persona.objects.filter(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']).order_by('tipo_persona', 'apellidos'):
                proy = None
                try:
                    if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz:
                        proy = p.perfil_aprendiz.proyecto
                except Exception:
                    pass
                lista.append((p, proy))
        elif grupo == 'aprendices':
            for a in Aprendiz.objects.select_related('persona', 'proyecto').order_by('persona__apellidos').all():
                lista.append((a.persona, a.proyecto))
        elif grupo == 'instructores':
            for i in Instructor.objects.select_related('persona').order_by('persona__apellidos').all():
                lista.append((i.persona, None))
        elif grupo == 'invitados':
            for i in Invitado.objects.select_related('persona').order_by('persona__apellidos').all():
                lista.append((i.persona, None))

        if not lista:
            messages.warning(request, 'No hay certificados para generar.')
            return redirect('simple:dashboard')

        buffer = generar_certificados_lote(lista, tipo=tipo, evento=evento)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="certificados_{tipo}_{grupo}.pdf"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp
