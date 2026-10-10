from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, DateField
from django.db.models.functions import TruncDate, Coalesce
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views import View
from django.utils import timezone

from apps.core.mixins import RoleRequiredMixin, AjaxLoginRequiredMixin
from apps.eventos.models import Evento
from apps.instituciones.models import InstitucionEducativa
from apps.programas.models import ProgramaTecnico
from apps.proyectos.models import Proyecto
from apps.instructores.models import Instructor
from apps.personas.models import Persona
from apps.asistencia.models import AsistenciaEvento
from apps.refrigerios.models import EntregaServicio
from apps.certificados.models import Certificado
from apps.usuarios.models import Usuario


ROLES_DASHBOARD = ['ADMINISTRADOR', 'REGISTRO', 'CONSULTA', 'GERENTE']

COLORES_SENA = {
    'verde': '#39A900',
    'verde_oscuro': '#2E7D32',
    'azul': '#0067B1',
    'naranja': '#F57C00',
    'amarillo': '#F9A825',
    'rojo': '#C62828',
    'gris': '#9E9E9E',
    'gris_oscuro': '#424242',
    'morado': '#7B1FA2',
}

PALETA_GRAFICOS = [
    '#39A900', '#0067B1', '#F57C00', '#F9A825', '#C62828',
    '#7B1FA2', '#00838F', '#5D4037', '#455A64', '#2E7D32',
    '#1565C0', '#EF6C00', '#AD1457', '#00695C', '#6A1B9A',
]


def _aplicar_filtros(request):
    evento_id = request.GET.get('evento') or ''
    institucion_id = request.GET.get('institucion') or ''
    municipio = request.GET.get('municipio') or ''
    programa_id = request.GET.get('programa') or ''
    proyecto_id = request.GET.get('proyecto') or ''
    instructor_id = request.GET.get('instructor') or ''
    tipo_persona = request.GET.get('tipo_persona') or ''

    evento = None
    if evento_id and evento_id.isdigit():
        try:
            evento = Evento.objects.get(pk=int(evento_id))
        except Evento.DoesNotExist:
            evento = Evento.objects.filter(activo=True).first()
    if not evento:
        evento = Evento.objects.filter(activo=True).first()

    proyectos_qs = Proyecto.objects.all()
    if evento:
        proyectos_qs = proyectos_qs.filter(evento=evento)
    if institucion_id and institucion_id.isdigit():
        proyectos_qs = proyectos_qs.filter(institucion_id=int(institucion_id))
    if municipio:
        proyectos_qs = proyectos_qs.filter(institucion__municipio__icontains=municipio.strip())
    if programa_id and programa_id.isdigit():
        proyectos_qs = proyectos_qs.filter(programa_id=int(programa_id))
    if proyecto_id and proyecto_id.isdigit():
        proyectos_qs = proyectos_qs.filter(pk=int(proyecto_id))
    if instructor_id and instructor_id.isdigit():
        proyectos_qs = proyectos_qs.filter(instructor_responsable_id=int(instructor_id))

    proyectos_ids = list(proyectos_qs.values_list('id', flat=True))

    personas_qs = Persona.objects.filter(activo=True)

    filtros_persona = Q()
    if tipo_persona:
        filtros_persona &= Q(tipo_persona=tipo_persona)

    q_aprendices = Q(perfil_aprendiz__proyecto_id__in=proyectos_ids) if proyectos_ids else Q(perfil_aprendiz__isnull=False)
    q_instructores_proy = Q(perfil_instructor__proyectos_dirigidos__id__in=proyectos_ids) if proyectos_ids else Q(perfil_instructor__isnull=False)
    if instructor_id and instructor_id.isdigit():
        q_instructores_proy = Q(perfil_instructor__pk=int(instructor_id))

    if evento or institucion_id or municipio or programa_id or proyecto_id or instructor_id:
        personas_qs = personas_qs.filter(
            filtros_persona & (q_aprendices | q_instructores_proy | Q(perfil_invitado__isnull=False))
        )
        if evento:
            personas_qs = personas_qs.filter(
                Q(asistencias__evento=evento)
                | Q(perfil_aprendiz__proyecto__evento=evento)
                | Q(perfil_instructor__proyectos_dirigidos__evento=evento)
                | Q(perfil_invitado__isnull=False)
            ).distinct()
    else:
        personas_qs = personas_qs.filter(filtros_persona)

    personas_qs = personas_qs.distinct()

    return {
        'evento': evento,
        'evento_id': evento.id if evento else None,
        'institucion_id': int(institucion_id) if institucion_id and institucion_id.isdigit() else None,
        'municipio': municipio.strip() if municipio else '',
        'programa_id': int(programa_id) if programa_id and programa_id.isdigit() else None,
        'proyecto_id': int(proyecto_id) if proyecto_id and proyecto_id.isdigit() else None,
        'instructor_id': int(instructor_id) if instructor_id and instructor_id.isdigit() else None,
        'tipo_persona': tipo_persona,
        'proyectos_qs': proyectos_qs.distinct(),
        'personas_qs': personas_qs,
    }


def _calcular_kpis(f):
    evento = f['evento']
    personas = f['personas_qs']
    proyectos = f['proyectos_qs']

    total_personas = personas.count()

    aprendices = personas.filter(perfil_aprendiz__isnull=False).count()
    instructores = personas.filter(perfil_instructor__isnull=False).count()
    invitados = personas.filter(perfil_invitado__isnull=False).count()

    total_proyectos = proyectos.count()

    instituciones_ids = proyectos.values_list('institucion_id', flat=True).distinct()
    total_instituciones = InstitucionEducativa.objects.filter(pk__in=list(instituciones_ids)).count() if instituciones_ids else 0

    programas_ids = proyectos.values_list('programa_id', flat=True).distinct()
    total_programas = ProgramaTecnico.objects.filter(pk__in=list(programas_ids)).count() if programas_ids else 0

    personas_ids = list(personas.values_list('id', flat=True))

    asistentes = 0
    if evento and personas_ids:
        asistentes = AsistenciaEvento.objects.filter(
            evento=evento, persona_id__in=personas_ids
        ).values('persona_id').distinct().count()

    ausentes = max(total_personas - asistentes, 0)

    porc_asistencia = 0.0
    if total_personas > 0:
        porc_asistencia = round((asistentes / total_personas) * 100, 1)

    refrigerios_entregados = 0
    if evento and personas_ids:
        refrigerios_entregados = EntregaServicio.objects.filter(
            evento=evento, persona_id__in=personas_ids
        ).count()

    num_servicios = 0
    if evento:
        num_servicios = evento.tipos_servicio.filter(activo=True).count()
    total_refrigerios_posibles = total_personas * max(num_servicios, 1) if num_servicios > 0 else refrigerios_entregados
    refrigerios_pendientes = max(total_refrigerios_posibles - refrigerios_entregados, 0)

    porc_refrigerios = 0.0
    if total_refrigerios_posibles > 0:
        porc_refrigerios = round((refrigerios_entregados / total_refrigerios_posibles) * 100, 1)

    certificados_entregados = 0
    if evento and personas_ids:
        certificados_entregados = Certificado.objects.filter(
            evento=evento, persona_id__in=personas_ids
        ).count()

    certificados_pendientes = max(total_personas - certificados_entregados, 0)

    porc_certificados = 0.0
    if total_personas > 0:
        porc_certificados = round((certificados_entregados / total_personas) * 100, 1)

    limite = timezone.now() - timedelta(minutes=15)
    operadores_conectados = Usuario.objects.filter(
        is_active=True,
        ultimo_acceso__gte=limite,
        rol_sistema__in=[
            'OPERADOR_ASISTENCIA',
            'OPERADOR_REFRIGERIO',
            'OPERADOR_CERTIFICADO',
            'ADMINISTRADOR',
            'REGISTRO',
        ],
    ).count()

    return {
        'participantes_registrados': total_personas,
        'aprendices': aprendices,
        'instructores': instructores,
        'invitados': invitados,
        'proyectos': total_proyectos,
        'instituciones': total_instituciones,
        'programas_tecnicos': total_programas,
        'asistentes': asistentes,
        'ausentes': ausentes,
        'porcentaje_asistencia': porc_asistencia,
        'refrigerios_entregados': refrigerios_entregados,
        'refrigerios_pendientes': refrigerios_pendientes,
        'porcentaje_refrigerios': porc_refrigerios,
        'certificados_entregados': certificados_entregados,
        'certificados_pendientes': certificados_pendientes,
        'porcentaje_certificados': porc_certificados,
        'operadores_conectados': operadores_conectados,
        'evento_nombre': evento.nombre if evento else 'Sin evento seleccionado',
    }


def _colorear(labels, start=0):
    n = len(labels)
    return [PALETA_GRAFICOS[(start + i) % len(PALETA_GRAFICOS)] for i in range(n)]


def _bg_with_alpha(colors, alpha=0.75):
    result = []
    for c in colors:
        if c.startswith('#') and len(c) == 7:
            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            result.append(f'rgba({r},{g},{b},{alpha})')
        else:
            result.append(c)
    return result


def _dataset(tipo, labels, data, idx=0, label=None, bg=None, border=None):
    colors = bg if bg else _colorear(labels, idx)
    return {
        'label': label or tipo,
        'data': list(data),
        'backgroundColor': colors if tipo in ('bar', 'pie', 'doughnut', 'polarArea') else _bg_with_alpha(colors[:1], 0.25),
        'borderColor': border if border else colors if tipo in ('bar', 'pie', 'doughnut', 'polarArea') else colors[:1],
        'borderWidth': 1,
    }


def _datasets_bar(labels, valores, idx=0, label='Cantidad'):
    return [_dataset('bar', labels, valores, idx=idx, label=label)]


def _datasets_stacked(labels, series):
    datasets = []
    for i, (lbl, vals) in enumerate(series):
        c = [PALETA_GRAFICOS[i % len(PALETA_GRAFICOS)]] * len(labels)
        datasets.append(_dataset('bar', labels, vals, idx=i, label=lbl, bg=c, border=c))
    return datasets


def _datasets_grouped(labels, series):
    return _datasets_stacked(labels, series)


def _calcular_grafico(tipo, f):
    evento = f['evento']
    personas = f['personas_qs']
    proyectos = f['proyectos_qs']
    personas_ids = list(personas.values_list('id', flat=True))

    if tipo == 'participantes_x_institucion':
        qs = (
            proyectos.values('institucion__nombre')
            .annotate(total=Count('aprendices__persona_id', distinct=True))
            .order_by('-total')[:20]
        )
        labels = [x['institucion__nombre'] or 'Sin institución' for x in qs]
        data = [x['total'] for x in qs]
        return {'labels': labels, 'datasets': _datasets_bar(labels, data, 0, 'Participantes')}

    if tipo == 'participantes_x_programa':
        qs = (
            proyectos.values('programa__nombre')
            .annotate(total=Count('aprendices__persona_id', distinct=True))
            .order_by('-total')[:20]
        )
        labels = [x['programa__nombre'] or 'Sin programa' for x in qs]
        data = [x['total'] for x in qs]
        return {'labels': labels, 'datasets': _datasets_bar(labels, data, 1, 'Participantes')}

    if tipo == 'proyectos_x_institucion':
        qs = (
            proyectos.values('institucion__nombre')
            .annotate(total=Count('id', distinct=True))
            .order_by('-total')[:20]
        )
        labels = [x['institucion__nombre'] or 'Sin institución' for x in qs]
        data = [x['total'] for x in qs]
        return {'labels': labels, 'datasets': _datasets_bar(labels, data, 2, 'Proyectos')}

    if tipo == 'proyectos_x_programa':
        qs = (
            proyectos.values('programa__nombre')
            .annotate(total=Count('id', distinct=True))
            .order_by('-total')[:20]
        )
        labels = [x['programa__nombre'] or 'Sin programa' for x in qs]
        data = [x['total'] for x in qs]
        return {'labels': labels, 'datasets': _datasets_bar(labels, data, 3, 'Proyectos')}

    if tipo == 'participantes_x_proyecto':
        qs = (
            proyectos.annotate(total=Count('aprendices__persona_id', distinct=True))
            .order_by('-total')[:15]
        )
        labels = [f"{p.codigo}" for p in qs]
        data = [p.total for p in qs]
        return {'labels': labels, 'datasets': _datasets_bar(labels, data, 4, 'Participantes')}

    if tipo == 'participantes_x_instructor':
        instr_qs = Instructor.objects.filter(proyectos_dirigidos__in=proyectos).distinct()
        labels = []
        data = []
        for ins in instr_qs:
            total = Persona.objects.filter(
                Q(perfil_aprendiz__proyecto__instructor_responsable=ins)
                | Q(perfil_instructor__pk=ins.pk)
            ).filter(pk__in=personas_ids).distinct().count() if personas_ids else 0
            labels.append(str(ins.persona.nombre_completo)[:30])
            data.append(total)
        orden = sorted(range(len(data)), key=lambda i: data[i], reverse=True)[:15]
        labels = [labels[i] for i in orden]
        data = [data[i] for i in orden]
        return {'labels': labels, 'datasets': _datasets_bar(labels, data, 5, 'Participantes')}

    if tipo == 'distribucion_tipo_persona':
        labels = ['Aprendices', 'Instructores', 'Invitados', 'Organizadores']
        qs = personas
        data = [
            qs.filter(tipo_persona='APRENDIZ').count(),
            qs.filter(tipo_persona='INSTRUCTOR').count(),
            qs.filter(tipo_persona='INVITADO').count(),
            qs.filter(tipo_persona='ORGANIZADOR').count(),
        ]
        bg = [COLORES_SENA['verde'], COLORES_SENA['azul'], COLORES_SENA['naranja'], COLORES_SENA['morado']]
        return {
            'labels': labels,
            'datasets': [_dataset('doughnut', labels, data, 0, 'Distribución', bg=bg, border=bg)],
        }

    if tipo == 'asistencia_general':
        total_p = personas.count()
        asistentes = 0
        if evento and personas_ids:
            asistentes = AsistenciaEvento.objects.filter(
                evento=evento, persona_id__in=personas_ids
            ).values('persona_id').distinct().count()
        ausentes = max(total_p - asistentes, 0)
        labels = ['Asistentes', 'Ausentes']
        data = [asistentes, ausentes]
        bg = [COLORES_SENA['verde_oscuro'], COLORES_SENA['rojo']]
        return {
            'labels': labels,
            'datasets': [_dataset('pie', labels, data, 0, 'Asistencia', bg=bg, border=bg)],
        }

    if tipo == 'asistencia_x_institucion':
        instituciones_qs = (
            proyectos.values_list('institucion__id', 'institucion__nombre').distinct()
        )
        labels = []
        asistencias = []
        ausencias = []
        for iid, nombre in instituciones_qs:
            perfiles = Persona.objects.filter(
                perfil_aprendiz__proyecto__institucion_id=iid,
                pk__in=personas_ids,
            ).distinct() if personas_ids else Persona.objects.none()
            tot = perfiles.count()
            asis = 0
            if evento and tot:
                asis = AsistenciaEvento.objects.filter(
                    evento=evento, persona__in=perfiles
                ).values('persona_id').distinct().count()
            labels.append(nombre or 'N/A')
            asistencias.append(asis)
            ausencias.append(max(tot - asis, 0))
        return {
            'labels': labels,
            'datasets': _datasets_stacked(labels, [('Asistentes', asistencias), ('Ausentes', ausencias)]),
        }

    if tipo == 'asistencia_x_programa':
        programas_qs = proyectos.values_list('programa__id', 'programa__nombre').distinct()
        labels = []
        asistencias = []
        ausencias = []
        for pid, nombre in programas_qs:
            perfiles = Persona.objects.filter(
                perfil_aprendiz__proyecto__programa_id=pid,
                pk__in=personas_ids,
            ).distinct() if personas_ids else Persona.objects.none()
            tot = perfiles.count()
            asis = 0
            if evento and tot:
                asis = AsistenciaEvento.objects.filter(
                    evento=evento, persona__in=perfiles
                ).values('persona_id').distinct().count()
            labels.append(nombre or 'N/A')
            asistencias.append(asis)
            ausencias.append(max(tot - asis, 0))
        return {
            'labels': labels,
            'datasets': _datasets_stacked(labels, [('Asistentes', asistencias), ('Ausentes', ausencias)]),
        }

    if tipo == 'refrigerios_x_tipo':
        labels = []
        entregados = []
        pendientes = []
        if evento:
            tipos = evento.tipos_servicio.all().order_by('orden', 'nombre')
            for ts in tipos:
                labels.append(ts.nombre)
                ent = 0
                if personas_ids:
                    ent = EntregaServicio.objects.filter(
                        evento=evento, tipo_servicio=ts, persona_id__in=personas_ids
                    ).count()
                entregados.append(ent)
                pendientes.append(max(len(personas_ids) - ent, 0))
        return {
            'labels': labels,
            'datasets': _datasets_grouped(labels, [('Entregados', entregados), ('Pendientes', pendientes)]),
        }

    if tipo == 'certificados_tiempo':
        labels = []
        data = []
        if evento:
            qs = (
                Certificado.objects.filter(evento=evento)
                .annotate(dia=TruncDate('fecha_hora_entrega', output_field=DateField()))
                .values('dia')
                .annotate(total=Count('id'))
                .order_by('dia')
            )
            for r in qs:
                labels.append(r['dia'].strftime('%d/%m') if r['dia'] else '')
                data.append(r['total'])
        return {
            'labels': labels,
            'datasets': [_dataset('line', labels, data, 0, 'Certificados entregados',
                                  bg=[COLORES_SENA['verde']], border=[COLORES_SENA['verde']])],
        }

    return {'labels': [], 'datasets': []}


TIPOS_GRAFICOS_MAP = {
    'participantes_x_institucion': 'bar',
    'participantes_x_programa': 'bar',
    'proyectos_x_institucion': 'bar',
    'proyectos_x_programa': 'bar',
    'participantes_x_proyecto': 'bar',
    'participantes_x_instructor': 'bar',
    'distribucion_tipo_persona': 'doughnut',
    'asistencia_general': 'pie',
    'asistencia_x_institucion': 'bar',
    'asistencia_x_programa': 'bar',
    'refrigerios_x_tipo': 'bar',
    'certificados_tiempo': 'line',
}


class PrincipalView(RoleRequiredMixin, LoginRequiredMixin, View):
    roles_requeridos = ROLES_DASHBOARD
    template_name = 'dashboard/principal.html'

    def get(self, request, *args, **kwargs):
        eventos = Evento.objects.filter(activo=True).order_by('-fecha_inicio')
        instituciones = InstitucionEducativa.objects.filter(activo=True).order_by('nombre')
        municipios = sorted(set(
            m[0] for m in InstitucionEducativa.objects.exclude(municipio='')
            .values_list('municipio') if m[0]
        ))
        programas = ProgramaTecnico.objects.filter(activo=True).order_by('nombre')
        proyectos_filtro = Proyecto.objects.select_related('evento').order_by('codigo')
        instructores = Instructor.objects.select_related('persona').filter(
            activo=True, persona__activo=True
        ).order_by('persona__apellidos', 'persona__nombres')

        evento_default = Evento.objects.filter(activo=True).first()
        sel_evento = request.GET.get('evento') or (str(evento_default.pk) if evento_default else '')

        ctx = {
            'eventos': eventos,
            'instituciones': instituciones,
            'municipios': municipios,
            'programas': programas,
            'proyectos': proyectos_filtro,
            'instructores': instructores,
            'tipos_persona': Persona.TIPOS,
            'sel_evento': sel_evento,
            'sel_institucion': request.GET.get('institucion', ''),
            'sel_municipio': request.GET.get('municipio', ''),
            'sel_programa': request.GET.get('programa', ''),
            'sel_proyecto': request.GET.get('proyecto', ''),
            'sel_instructor': request.GET.get('instructor', ''),
            'sel_tipo_persona': request.GET.get('tipo_persona', ''),
        }
        return TemplateResponse(request, self.template_name, ctx)


class KpisJsonView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ROLES_DASHBOARD

    def get(self, request, *args, **kwargs):
        f = _aplicar_filtros(request)
        kpis = _calcular_kpis(f)
        return JsonResponse({'ok': True, 'kpis': kpis}, json_dumps_params={'ensure_ascii': False})


class GraficosJsonView(AjaxLoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ROLES_DASHBOARD

    def get(self, request, *args, **kwargs):
        f = _aplicar_filtros(request)
        tipos_solicitados = request.GET.getlist('tipo')
        if not tipos_solicitados:
            tipos_solicitados = list(TIPOS_GRAFICOS_MAP.keys())

        resultado = {}
        for t in tipos_solicitados:
            if t in TIPOS_GRAFICOS_MAP:
                datos = _calcular_grafico(t, f)
                resultado[t] = {
                    'type': TIPOS_GRAFICOS_MAP[t],
                    'labels': datos.get('labels', []),
                    'datasets': datos.get('datasets', []),
                }
        return JsonResponse({'ok': True, 'graficos': resultado}, json_dumps_params={'ensure_ascii': False})
