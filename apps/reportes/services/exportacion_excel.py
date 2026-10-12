"""Servicios de exportación de reportes a Excel usando openpyxl."""
import io
from datetime import datetime

from django.db.models import Count, Q
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ── Estilos ──────────────────────────────────────────────────────────────
COLOR_VERDE = "39A900"
COLOR_VERDE_OSCURO = "2D7A00"
COLOR_BLANCO = "FFFFFF"
COLOR_GRIS = "F5F5F5"

_fill_header = PatternFill(start_color=COLOR_VERDE, end_color=COLOR_VERDE, fill_type="solid")
_fill_alt = PatternFill(start_color=COLOR_GRIS, end_color=COLOR_GRIS, fill_type="solid")
_font_header = Font(name="Calibri", size=11, bold=True, color=COLOR_BLANCO)
_font_cell = Font(name="Calibri", size=10)
_align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
_align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
_border = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)


def _crear_libro():
    wb = Workbook()
    return wb


def _aplicar_estilos(ws, num_cols, encabezados=True):
    """Aplica estilos a encabezados y anchos de columna automáticos."""
    if encabezados:
        for col in range(1, num_cols + 1):
            cell = ws.cell(row=1, column=col)
            cell.fill = _fill_header
            cell.font = _font_header
            cell.alignment = _align_center
            cell.border = _border
    # Ancho automático basado en contenido
    for col in range(1, num_cols + 1):
        max_len = 10
        col_letter = get_column_letter(col)
        for row in ws.iter_rows(min_col=col, max_col=col, values_only=True):
            for val in row:
                if val:
                    max_len = max(max_len, min(len(str(val)), 50))
        ws.column_dimensions[col_letter].width = max_len + 2


def _escribir_filas(ws, filas, start_row=2):
    """Escribe filas de datos con formato alternado."""
    for i, fila in enumerate(filas):
        row_num = start_row + i
        fill = _fill_alt if i % 2 == 1 else None
        for j, val in enumerate(fila):
            cell = ws.cell(row=row_num, column=j + 1, value=val)
            cell.font = _font_cell
            cell.border = _border
            cell.alignment = _align_left if j > 0 else _align_center
            if fill:
                cell.fill = fill


def _respuesta_excel(wb, nombre_archivo):
    """Convierte el Workbook en HttpResponse con el archivo adjunto."""
    from django.http import HttpResponse

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return response


def _evento_activo():
    from apps.eventos.models import Evento
    return Evento.objects.filter(activo=True, estado="ACTIVO").order_by("-fecha_inicio").first()


# ── Reportes ─────────────────────────────────────────────────────────────

def reporte_participantes(evento=None):
    """Listado completo de personas del evento."""
    from apps.personas.models import Persona

    if evento is None:
        evento = _evento_activo()

    personas = Persona.objects.all().order_by("tipo_persona", "apellidos", "nombres")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Participantes"

    headers = ["#", "Tipo", "Identificación", "Nombres", "Apellidos", "Teléfono", "Email"]
    ws.append(headers)

    filas = []
    for i, p in enumerate(personas, 1):
        filas.append([
            i,
            p.get_tipo_persona_display() or p.tipo_persona,
            f"{p.tipo_identificacion.codigo} {p.numero_identificacion}" if p.tipo_identificacion_id else p.numero_identificacion,
            p.nombres or "",
            p.apellidos or "",
            p.telefono or "",
            p.email or "",
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"participantes_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_asistentes(evento=None):
    """Personas que registraron asistencia con fecha/hora/operador."""
    from apps.asistencia.models import AsistenciaEvento

    if evento is None:
        evento = _evento_activo()

    qs = AsistenciaEvento.objects.select_related("persona", "operador", "evento")
    if evento:
        qs = qs.filter(evento=evento)
    qs = qs.order_by("fecha_hora")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Asistentes"

    headers = ["#", "Fecha", "Hora", "Identificación", "Nombres", "Apellidos", "Tipo", "Operador"]
    ws.append(headers)

    filas = []
    for i, a in enumerate(qs, 1):
        filas.append([
            i,
            a.fecha_hora.date().isoformat() if a.fecha_hora else "",
            a.fecha_hora.time().strftime("%H:%M:%S") if a.fecha_hora else "",
            f"{a.persona.tipo_identificacion.codigo} {a.persona.numero_identificacion}" if a.persona.tipo_identificacion_id else a.persona.numero_identificacion,
            a.persona.nombres or "",
            a.persona.apellidos or "",
            a.persona.get_tipo_persona_display() or a.persona.tipo_persona,
            a.operador.username if a.operador_id else "",
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"asistentes_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_ausentes(evento=None):
    """Personas que NUNCA registraron asistencia."""
    from apps.personas.models import Persona
    from apps.asistencia.models import AsistenciaEvento

    if evento is None:
        evento = _evento_activo()

    # IDs de personas que asistieron
    ids_asistentes = AsistenciaEvento.objects.filter(evento=evento).values_list("persona_id", flat=True) if evento else AsistenciaEvento.objects.values_list("persona_id", flat=True)

    ausentes = Persona.objects.exclude(id__in=ids_asistentes).order_by("tipo_persona", "apellidos", "nombres")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Ausentes"

    headers = ["#", "Tipo", "Identificación", "Nombres", "Apellidos", "Teléfono", "Email"]
    ws.append(headers)

    filas = []
    for i, p in enumerate(ausentes, 1):
        filas.append([
            i,
            p.get_tipo_persona_display() or p.tipo_persona,
            f"{p.tipo_identificacion.codigo} {p.numero_identificacion}" if p.tipo_identificacion_id else p.numero_identificacion,
            p.nombres or "",
            p.apellidos or "",
            p.telefono or "",
            p.email or "",
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"ausentes_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_refrigerios(evento=None):
    """Entregas de refrigerios por tipo de servicio."""
    from apps.refrigerios.models import EntregaServicio

    if evento is None:
        evento = _evento_activo()

    qs = EntregaServicio.objects.select_related("persona", "tipo_servicio", "operador", "evento")
    if evento:
        qs = qs.filter(evento=evento)
    qs = qs.order_by("fecha_hora")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Refrigerios"

    headers = ["#", "Fecha", "Hora", "Servicio", "Identificación", "Nombres", "Apellidos", "Tipo", "Operador"]
    ws.append(headers)

    filas = []
    for i, e in enumerate(qs, 1):
        filas.append([
            i,
            e.fecha_hora.date().isoformat() if e.fecha_hora else "",
            e.fecha_hora.time().strftime("%H:%M:%S") if e.fecha_hora else "",
            e.tipo_servicio.nombre if e.tipo_servicio_id else "",
            f"{e.persona.tipo_identificacion.codigo} {e.persona.numero_identificacion}" if e.persona.tipo_identificacion_id else e.persona.numero_identificacion,
            e.persona.nombres or "",
            e.persona.apellidos or "",
            e.persona.get_tipo_persona_display() or e.persona.tipo_persona,
            e.operador.username if e.operador_id else "",
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"refrigerios_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_certificados(evento=None):
    """Certificados entregados con código y token de verificación."""
    from apps.certificados.models import Certificado

    if evento is None:
        evento = _evento_activo()

    qs = Certificado.objects.select_related("persona", "operador", "evento")
    if evento:
        qs = qs.filter(evento=evento)
    qs = qs.order_by("fecha_hora_entrega")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Certificados"

    headers = ["#", "Fecha Entrega", "Hora", "Código", "Token Verificación", "Identificación", "Nombres", "Apellidos", "Tipo", "Operador"]
    ws.append(headers)

    filas = []
    for i, c in enumerate(qs, 1):
        filas.append([
            i,
            c.fecha_hora_entrega.date().isoformat() if c.fecha_hora_entrega else "",
            c.fecha_hora_entrega.time().strftime("%H:%M:%S") if c.fecha_hora_entrega else "",
            c.codigo_unico or "",
            str(c.token_verificacion) if c.token_verificacion else "",
            f"{c.persona.tipo_identificacion.codigo} {c.persona.numero_identificacion}" if c.persona.tipo_identificacion_id else c.persona.numero_identificacion,
            c.persona.nombres or "",
            c.persona.apellidos or "",
            c.persona.get_tipo_persona_display() or c.persona.tipo_persona,
            c.operador.username if c.operador_id else "",
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"certificados_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_instituciones(evento=None):
    """Consolidado de instituciones educativas."""
    from apps.instituciones.models import InstitucionEducativa
    from apps.proyectos.models import Proyecto

    if evento is None:
        evento = _evento_activo()

    instituciones = InstitucionEducativa.objects.all().order_by("nombre")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Instituciones"

    headers = ["#", "Código", "Nombre", "Municipio", "Departamento", "Nivel", "Estado", "# Proyectos"]
    ws.append(headers)

    filas = []
    for i, inst in enumerate(instituciones, 1):
        n_proy = Proyecto.objects.filter(institucion=inst, evento=evento).count() if evento else 0
        filas.append([
            i,
            inst.codigo or "",
            inst.nombre or "",
            getattr(inst, "municipio", "") or "",
            getattr(inst, "departamento", "") or "",
            getattr(inst, "nivel", "") or "",
            "Activo" if inst.activo else "Inactivo",
            n_proy,
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"instituciones_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_programas(evento=None):
    """Consolidado de programas técnicos."""
    from apps.programas.models import ProgramaTecnico
    from apps.proyectos.models import Proyecto

    if evento is None:
        evento = _evento_activo()

    programas = ProgramaTecnico.objects.all().order_by("nombre")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Programas"

    headers = ["#", "Código", "Nombre", "Nivel", "Estado", "# Proyectos"]
    ws.append(headers)

    filas = []
    for i, prog in enumerate(programas, 1):
        n_proy = Proyecto.objects.filter(programa=prog, evento=evento).count() if evento else 0
        filas.append([
            i,
            prog.codigo or "",
            prog.nombre or "",
            getattr(prog, "nivel", "") or "",
            "Activo" if prog.activo else "Inactivo",
            n_proy,
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"programas_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_proyectos(evento=None):
    """Listado de proyectos."""
    from apps.proyectos.models import Proyecto

    if evento is None:
        evento = _evento_activo()

    qs = Proyecto.objects.select_related("ficha", "institucion", "programa", "instructor_responsable", "evento")
    if evento:
        qs = qs.filter(evento=evento)
    qs = qs.order_by("codigo")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Proyectos"

    headers = ["#", "Código", "Nombre", "Ficha", "Institución", "Programa", "Instructor", "Estado"]
    ws.append(headers)

    filas = []
    for i, p in enumerate(qs, 1):
        filas.append([
            i,
            p.codigo or "",
            p.nombre or "",
            p.ficha.numero if p.ficha_id else "",
            p.institucion.nombre if p.institucion_id else "",
            p.programa.nombre if p.programa_id else "",
            p.instructor_responsable.persona.nombre_completo if p.instructor_responsable_id else "",
            p.get_estado_display() or p.estado,
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"proyectos_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_proyectos_detalle(evento=None):
    """Proyectos + listado de aprendices."""
    from apps.proyectos.models import Proyecto, Aprendiz

    if evento is None:
        evento = _evento_activo()

    qs = Proyecto.objects.select_related("ficha", "institucion", "programa", "instructor_responsable", "evento")
    if evento:
        qs = qs.filter(evento=evento)
    qs = qs.order_by("codigo")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Proyectos Detalle"

    headers = ["#", "Código", "Proyecto", "Ficha", "Institución", "Programa", "Aprendiz", "Identificación", "Estado Proyecto"]
    ws.append(headers)

    filas = []
    idx = 1
    for p in qs:
        aprendices = Aprendiz.objects.filter(proyecto=p).select_related("persona", "persona__tipo_identificacion")
        if not aprendices.exists():
            filas.append([
                idx, p.codigo or "", p.nombre or "",
                p.ficha.numero if p.ficha_id else "",
                p.institucion.nombre if p.institucion_id else "",
                p.programa.nombre if p.programa_id else "",
                "(sin aprendices)", "",
                p.get_estado_display() or p.estado,
            ])
            idx += 1
        else:
            for ap in aprendices:
                filas.append([
                    idx, p.codigo or "", p.nombre or "",
                    p.ficha.numero if p.ficha_id else "",
                    p.institucion.nombre if p.institucion_id else "",
                    p.programa.nombre if p.programa_id else "",
                    ap.persona.nombre_completo,
                    f"{ap.persona.tipo_identificacion.codigo} {ap.persona.numero_identificacion}" if ap.persona.tipo_identificacion_id else ap.persona.numero_identificacion,
                    p.get_estado_display() or p.estado,
                ])
                idx += 1

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"proyectos_detalle_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_instructores_consolidado(evento=None):
    """Instructores + proyectos asignados."""
    from apps.instructores.models import Instructor
    from apps.proyectos.models import Proyecto

    if evento is None:
        evento = _evento_activo()

    instructores = Instructor.objects.select_related("persona").order_by("persona__apellidos", "persona__nombres")

    wb = _crear_libro()
    ws = wb.active
    ws.title = "Instructores"

    headers = ["#", "Identificación", "Nombres", "Apellidos", "Teléfono", "Email", "# Proyectos"]
    ws.append(headers)

    filas = []
    for i, inst in enumerate(instructores, 1):
        n_proy = Proyecto.objects.filter(instructor_responsable=inst, evento=evento).count() if evento else 0
        p = inst.persona
        filas.append([
            i,
            f"{p.tipo_identificacion.codigo} {p.numero_identificacion}" if p.tipo_identificacion_id else p.numero_identificacion,
            p.nombres or "",
            p.apellidos or "",
            p.telefono or "",
            p.email or "",
            n_proy,
        ])

    _escribir_filas(ws, filas)
    _aplicar_estilos(ws, len(headers))
    ws.freeze_panes = "A2"
    return _respuesta_excel(wb, f"instructores_{datetime.now():%Y%m%d_%H%M}.xlsx")


def reporte_general_excel(evento=None):
    """Reporte general con KPIs, Institución y Programa."""
    if evento is None:
        evento = _evento_activo()

    from apps.personas.models import Persona
    from apps.asistencia.models import AsistenciaEvento
    from apps.refrigerios.models import EntregaServicio
    from apps.certificados.models import Certificado
    from apps.proyectos.models import Proyecto, Aprendiz
    from apps.instituciones.models import InstitucionEducativa
    from apps.programas.models import ProgramaTecnico

    wb = _crear_libro()

    # ── Hoja 1: KPIs ──
    ws1 = wb.active
    ws1.title = "KPIs"

    total_personas = Persona.objects.count()
    total_asistentes = AsistenciaEvento.objects.filter(evento=evento).count() if evento else AsistenciaEvento.objects.count()
    total_ausentes = total_personas - total_asistentes
    total_refrigerios = EntregaServicio.objects.filter(evento=evento).count() if evento else EntregaServicio.objects.count()
    total_certificados = Certificado.objects.filter(evento=evento).count() if evento else Certificado.objects.count()
    total_proyectos = Proyecto.objects.filter(evento=evento).count() if evento else Proyecto.objects.count()
    total_aprendices = Aprendiz.objects.filter(proyecto__evento=evento).count() if evento else Aprendiz.objects.count()
    total_instituciones = InstitucionEducativa.objects.count()
    total_programas = ProgramaTecnico.objects.count()

    headers_kpi = ["Indicador", "Valor"]
    ws1.append(headers_kpi)
    filas_kpi = [
        ["Evento", evento.nombre if evento else "Sin evento activo"],
        ["Total Personas Registradas", total_personas],
        ["Total Asistentes", total_asistentes],
        ["Total Ausentes", total_ausentes],
        ["% Asistencia", f"{(total_asistentes / total_personas * 100):.1f}%" if total_personas > 0 else "0%"],
        ["Total Refrigerios Entregados", total_refrigerios],
        ["Total Certificados Entregados", total_certificados],
        ["Total Proyectos", total_proyectos],
        ["Total Aprendices", total_aprendices],
        ["Total Instituciones", total_instituciones],
        ["Total Programas", total_programas],
    ]
    _escribir_filas(ws1, filas_kpi)
    _aplicar_estilos(ws1, len(headers_kpi))

    # ── Hoja 2: Por Institución ──
    ws2 = wb.create_sheet("Por Institución")
    headers2 = ["#", "Institución", "# Proyectos", "# Aprendices"]
    ws2.append(headers2)
    filas2 = []
    for i, inst in enumerate(InstitucionEducativa.objects.all().order_by("nombre"), 1):
        n_proy = Proyecto.objects.filter(institucion=inst, evento=evento).count() if evento else 0
        n_apr = Aprendiz.objects.filter(proyecto__institucion=inst, proyecto__evento=evento).count() if evento else 0
        filas2.append([i, inst.nombre or "", n_proy, n_apr])
    _escribir_filas(ws2, filas2)
    _aplicar_estilos(ws2, len(headers2))

    # ── Hoja 3: Por Programa ──
    ws3 = wb.create_sheet("Por Programa")
    headers3 = ["#", "Programa", "# Proyectos", "# Aprendices"]
    ws3.append(headers3)
    filas3 = []
    for i, prog in enumerate(ProgramaTecnico.objects.all().order_by("nombre"), 1):
        n_proy = Proyecto.objects.filter(programa=prog, evento=evento).count() if evento else 0
        n_apr = Aprendiz.objects.filter(proyecto__programa=prog, proyecto__evento=evento).count() if evento else 0
        filas3.append([i, prog.nombre or "", n_proy, n_apr])
    _escribir_filas(ws3, filas3)
    _aplicar_estilos(ws3, len(headers3))

    return _respuesta_excel(wb, f"reporte_general_{datetime.now():%Y%m%d_%H%M}.xlsx")
