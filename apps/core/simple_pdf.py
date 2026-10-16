import os
from io import BytesIO
from pathlib import Path

from django.http import HttpResponse
from django.conf import settings

# Ruta de la imagen de fondo para certificados
_CERT_FONDO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'static', 'img', 'Certificado FERIA SENA.png'
)

from reportlab.lib.pagesizes import A4, landscape, A6
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import shapes
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

try:
    from PIL import Image as PILImage
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False


SENA_VERDE = HexColor('#39A900')
SENA_AZUL = HexColor('#0067B1')
SENA_NARANJA = HexColor('#F57C00')
SENA_GRIS = HexColor('#555555')
SENA_BG_LIGHT = HexColor('#EEF8E7')


def _path_logo():
    static = Path(settings.STATICFILES_DIRS[0] if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS else (settings.BASE_DIR / 'static'))
    for name in ['logo-sena-verde.png', 'logo-sena.png', 'logo-sena.svg', 'sena_logo.png']:
        p = static / 'img' / name
        if p.exists():
            return str(p)
    return None


def _dibujar_qr_bytes(dato, tamano_mm=30):
    from reportlab.graphics.barcode.qr import QrCodeWidget
    tamano = tamano_mm * mm
    qrw = QrCodeWidget(dato, barLevel='M', barWidth=tamano, barHeight=tamano)
    d = Drawing(tamano, tamano)
    d.add(shapes.Rect(0, 0, tamano, tamano, fillColor=white, strokeColor=None))
    qrw.x = 0
    qrw.y = 0
    qrw.barWidth = tamano
    qrw.barHeight = tamano
    d.add(qrw)
    return d


def _estilos():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SenaVerde', textColor=SENA_VERDE, fontName='Helvetica-Bold', leading=16))
    styles.add(ParagraphStyle(name='SenaChico', textColor=SENA_GRIS, fontName='Helvetica', fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='SenaTitulo', textColor=SENA_VERDE, fontName='Helvetica-Bold', fontSize=14, leading=18, alignment=1))
    styles.add(ParagraphStyle(name='SenaSubtitulo', textColor=SENA_AZUL, fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=1))
    styles.add(ParagraphStyle(name='SenaNombre', textColor=black, fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=1))
    styles.add(ParagraphStyle(name='SenaRol', textColor=SENA_AZUL, fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=1))
    styles.add(ParagraphStyle(name='SenaInfo', textColor=SENA_GRIS, fontName='Helvetica', fontSize=8, leading=10, alignment=1))
    return styles


def _construir_logo_centrado(styles, ancho_mm=28, alto_mm=28):
    """Devuelve un logo SENA centrado (institucional) con fallback de texto."""
    logo_path = _path_logo()
    if logo_path and _HAS_PIL:
        try:
            return Image(logo_path, width=ancho_mm * mm, height=alto_mm * mm, hAlign='CENTER')
        except Exception:
            pass
    return Paragraph('SENA', styles['SenaTitulo'])


# =======================================================================
# ESCARAPELAS 107mm × 135mm RETRATO DÚPLEX (2 páginas por persona)
#  — Wrappers al servicio nuevo EscarapelaPDFService —
#  Generación:
#   - INDIVIDUAL: 107×135mm, 2 páginas dúplex por persona
#   - LOTE 4x CARTA (Letter): 4 escarapelas por hoja CARTA (grid 2×2)
#     Estructura de lote = Bloque I (TODOS los frentes 4x hoja)
#                        + Bloque II (TODOS los reversos 4x hoja)
#     Así al imprimir dúplex por hojas, al cortar 2x2 salen 4 dúplex.
# =======================================================================
def generar_escarapela_individual(persona, evento=None, proyecto=None, buffer=None):
    from apps.escarapelas.services import EscarapelaPDFService
    return EscarapelaPDFService.generar_individual(persona, evento)


def generar_escarapelas_lote(lista_items, evento=None, nombre_archivo='escarapelas.pdf', formato='CARTA_4X'):
    from apps.escarapelas.services import EscarapelaPDFService
    personas = []
    for item in lista_items:
        if isinstance(item, tuple):
            personas.append(item[0])
        else:
            personas.append(item)
    return EscarapelaPDFService.generar_lote(personas, evento, nombre_archivo, formato=formato)


# =======================================================================
# CERTIFICADOS EDITABLES (formulario configurable) - Asistencia / Participación
# =======================================================================
PLANTILLAS_CERTIFICADO = {
    'ASISTENCIA': {
        'titulo': 'CERTIFICADO DE ASISTENCIA',
        'parrafo_intro': 'El Sistema de Gestión de la Feria de Proyectos Productivos del <b>SENA - Regional Guajira</b>, certifica que:',
        'parrafo_central': '<b>{NOMBRE_COMPLETO}</b>, identificado(a) con <b>{TIPO_ID}</b> N° <b>{NUMERO_ID}</b>, participó en el evento <b>{EVENTO}</b> realizado en <b>{LUGAR}</b>, Municipio de <b>{MUNICIPIO}</b>, durante las fechas <b>{FECHA_INICIO}</b> al <b>{FECHA_FIN}</b>.',
        'parrafo_final': 'Y para constancia y fines a que haya lugar, se firma la presente en el Municipio de <b>{MUNICIPIO}</b>, a los <b>{FECHA_EMISION}</b>.',
        'firma_1_nombre': 'COORDINADOR FERIA',
        'firma_1_cargo': 'Coordinador Regional - SENA Guajira',
        'firma_2_nombre': 'LÍDER LOGÍSTICA',
        'firma_2_cargo': 'Gestión Operativa',
    },
    'PARTICIPACION': {
        'titulo': 'CERTIFICADO DE PARTICIPACIÓN EN PROYECTO',
        'parrafo_intro': 'El Sistema de Gestión de la Feria de Proyectos Productivos del <b>SENA - Regional Guajira</b>, certifica con orgullo que:',
        'parrafo_central': '<b>{NOMBRE_COMPLETO}</b>, con <b>{ROL}</b> en el proyecto <b>{NOMBRE_PROYECTO}</b>, código <b>{CODIGO_PROYECTO}</b>, presentado por la Institución Educativa <b>{INSTITUCION}</b>, Municipio de <b>{MUNICIPIO}</b>, participó exitosamente en <b>{EVENTO}</b> realizado en <b>{LUGAR}</b> del <b>{FECHA_INICIO}</b> al <b>{FECHA_FIN}</b>.',
        'parrafo_final': 'Este certificado se expide a solicitud del interesado a los <b>{FECHA_EMISION}</b>.',
        'firma_1_nombre': 'INSTRUCTOR LÍDER',
        'firma_1_cargo': 'Tutor del Proyecto',
        'firma_2_nombre': 'JURADO TÉCNICO',
        'firma_2_cargo': 'Evaluación del Proyecto',
    },
}


def _reemplazar_plantilla(plantilla, persona, evento=None, proyecto=None, overrides=None):
    overrides = overrides or {}
    from datetime import date

    try:
        tipo_id_nice = persona.tipo_identificacion.nombre if persona.tipo_identificacion else 'Cédula'
    except Exception:
        tipo_id_nice = 'Cédula'
    rol_nice = {'APRENDIZ': 'Aprendiz', 'INSTRUCTOR': 'Instructor',
                'INVITADO': 'Invitado', 'ORGANIZADOR': 'Organizador',
                'ACUDIENTE': 'Acudiente'}.get(persona.tipo_persona or '', 'Participante')
    nombre_institucion = ''
    nombre_proyecto = ''
    codigo_proyecto = ''
    if proyecto:
        nombre_proyecto = proyecto.nombre or ''
        codigo_proyecto = proyecto.codigo or ''
        if proyecto.institucion:
            nombre_institucion = proyecto.institucion.nombre or ''
    elif persona.tipo_persona == 'APRENDIZ':
        try:
            if hasattr(persona, 'perfil_aprendiz') and persona.perfil_aprendiz and persona.perfil_aprendiz.proyecto:
                p = persona.perfil_aprendiz.proyecto
                nombre_proyecto = p.nombre or ''
                codigo_proyecto = p.codigo or ''
                if p.institucion:
                    nombre_institucion = p.institucion.nombre or ''
        except Exception:
            pass

    fecha_emision = overrides.get('FECHA_EMISION') or date.today().strftime('%d de %B de %Y')

    vars_ = {
        'NOMBRE_COMPLETO': overrides.get('NOMBRE_COMPLETO') or persona.get_full_name(),
        'TIPO_ID': overrides.get('TIPO_ID') or tipo_id_nice,
        'NUMERO_ID': overrides.get('NUMERO_ID') or persona.numero_identificacion,
        'EVENTO': overrides.get('EVENTO') or (evento.nombre if evento else 'Feria Proyectos Productivos SENA'),
        'LUGAR': overrides.get('LUGAR') or (evento.lugar if evento else 'Sede Principal SENA'),
        'MUNICIPIO': overrides.get('MUNICIPIO') or (evento.municipio if evento else 'Riohacha'),
        'FECHA_INICIO': overrides.get('FECHA_INICIO') or (str(evento.fecha_inicio) if evento and evento.fecha_inicio else ''),
        'FECHA_FIN': overrides.get('FECHA_FIN') or (str(evento.fecha_fin) if evento and evento.fecha_fin else ''),
        'FECHA_EMISION': fecha_emision,
        'ROL': overrides.get('ROL') or rol_nice,
        'NOMBRE_PROYECTO': overrides.get('NOMBRE_PROYECTO') or nombre_proyecto,
        'CODIGO_PROYECTO': overrides.get('CODIGO_PROYECTO') or codigo_proyecto,
        'INSTITUCION': overrides.get('INSTITUCION') or nombre_institucion,
        'FIRMA_1_NOMBRE': overrides.get('FIRMA_1_NOMBRE') or plantilla.get('firma_1_nombre', ''),
        'FIRMA_1_CARGO': overrides.get('FIRMA_1_CARGO') or plantilla.get('firma_1_cargo', ''),
        'FIRMA_2_NOMBRE': overrides.get('FIRMA_2_NOMBRE') or plantilla.get('firma_2_nombre', ''),
        'FIRMA_2_CARGO': overrides.get('FIRMA_2_CARGO') or plantilla.get('firma_2_cargo', ''),
    }
    return vars_


def generar_certificado_pdf(persona, tipo='ASISTENCIA', evento=None, proyecto=None, overrides=None, buffer=None):
    """Genera un certificado individual usando la imagen de fondo 'Certificado FERIA SENA.png'."""
    from reportlab.lib.colors import HexColor, black
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as canvas_mod

    tipo = (tipo or 'ASISTENCIA').upper()
    plantilla = PLANTILLAS_CERTIFICADO.get(tipo, PLANTILLAS_CERTIFICADO['ASISTENCIA'])
    vars_ = _reemplazar_plantilla(plantilla, persona, evento=evento, proyecto=proyecto, overrides=overrides)

    if buffer is None:
        buffer = BytesIO()

    page_w, page_h = letter  # 612 x 792 pt
    c = canvas_mod.Canvas(buffer, pagesize=letter)

    SENA_VERDE_OSCURO = HexColor('#1B5E20')
    SENA_AZUL = HexColor('#0D47A1')

    # --- Imagen de fondo (ocupa toda la página) ---
    if os.path.isfile(_CERT_FONDO_PATH):
        try:
            c.drawImage(_CERT_FONDO_PATH, 0, 0, width=page_w, height=page_h,
                        preserveAspectRatio=True, anchor='c')
        except Exception:
            pass

    # --- Nombre de la persona (debajo de 'SE OTORGA AL PROYECTO') ---
    nombre_persona = (getattr(persona, 'nombre_completo', '') or '').strip().upper()
    max_w = page_w - 40 * mm
    fs = 16
    while fs > 10 and stringWidth(nombre_persona, 'Helvetica-Bold', fs) > max_w:
        fs -= 0.5
    c.setFillColor(black)
    c.setFont('Helvetica-Bold', fs)
    # Posición: ~47% desde arriba
    c.drawCentredString(page_w / 2, page_h * 0.53, nombre_persona)

    # --- Nombre del proyecto o institución (debajo de 'DE LA INSTITUCIÓN EDUCATIVA') ---
    texto_secundario = ''
    try:
        if proyecto:
            texto_secundario = (getattr(proyecto, 'nombre', '') or '').strip().upper()
        elif getattr(persona, 'institucion', None) and persona.institucion:
            texto_secundario = (getattr(persona.institucion, 'nombre', '') or '').strip().upper()
    except Exception:
        pass
    fs2 = 13
    while fs2 > 8 and stringWidth(texto_secundario, 'Helvetica-Bold', fs2) > max_w:
        fs2 -= 0.5
    c.setFillColor(SENA_VERDE_OSCURO)
    c.setFont('Helvetica-Bold', fs2)
    # Posición: ~38% desde arriba
    c.drawCentredString(page_w / 2, page_h * 0.38, texto_secundario)

    # --- Documento de la persona (esquina inferior izquierda) ---
    doc_texto = f'Doc: {getattr(persona, "numero_identificacion", "") or ""}'
    c.setFillColor(SENA_AZUL)
    c.setFont('Helvetica', 7)
    c.drawString(10 * mm, 10 * mm, doc_texto)

    # --- QR (esquina inferior derecha) ---
    qr_token = getattr(persona, 'qr_token', None)
    qr_size = 24 * mm
    qr_x = page_w - qr_size - 10 * mm
    qr_y = 10 * mm
    if qr_token:
        try:
            from reportlab.graphics.barcode.qr import QrCodeWidget
            from reportlab.graphics.shapes import Drawing
            qrw = QrCodeWidget(str(qr_token), barLevel='M', barWidth=qr_size, barHeight=qr_size)
            d = Drawing(qr_size, qr_size)
            d.add(qrw)
            d.drawOn(c, qr_x, qr_y)
        except Exception:
            pass
    # Etiqueta del QR
    c.setFillColor(HexColor('#555555'))
    c.setFont('Helvetica', 6)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, 'Escanea para verificar')

    c.save()
    buffer.seek(0)
    return buffer


def generar_certificados_lote(lista, tipo='ASISTENCIA', evento=None):
    """Genera un PDF con múltiples certificados individuales (1 por página) usando la imagen de fondo."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as canvas_mod

    buffer = BytesIO()
    page_w, page_h = letter
    c = canvas_mod.Canvas(buffer, pagesize=letter)

    for idx, item in enumerate(lista):
        if isinstance(item, tuple):
            persona, proyecto = item
        else:
            persona, proyecto = item, None

        # Dibuja el certificado en la página actual
        _draw_certificado_individual(c, page_w, page_h, persona, proyecto=proyecto)

        # Pasar de página (excepto en el último)
        if idx < len(lista) - 1:
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


def _draw_certificado_individual(canvas, page_w, page_h, persona, proyecto=None):
    """Dibuja un certificado individual sobre la imagen de fondo."""
    from reportlab.lib.colors import HexColor, black
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth

    SENA_VERDE_OSCURO = HexColor('#1B5E20')
    SENA_AZUL = HexColor('#0D47A1')

    # Imagen de fondo
    if os.path.isfile(_CERT_FONDO_PATH):
        try:
            canvas.drawImage(_CERT_FONDO_PATH, 0, 0, width=page_w, height=page_h,
                             preserveAspectRatio=True, anchor='c')
        except Exception:
            pass

    # Nombre de la persona
    nombre_persona = (getattr(persona, 'nombre_completo', '') or '').strip().upper()
    max_w = page_w - 40 * mm
    fs = 16
    while fs > 10 and stringWidth(nombre_persona, 'Helvetica-Bold', fs) > max_w:
        fs -= 0.5
    canvas.setFillColor(black)
    canvas.setFont('Helvetica-Bold', fs)
    canvas.drawCentredString(page_w / 2, page_h * 0.53, nombre_persona)

    # Proyecto o institución
    texto_secundario = ''
    try:
        if proyecto:
            texto_secundario = (getattr(proyecto, 'nombre', '') or '').strip().upper()
        elif getattr(persona, 'institucion', None) and persona.institucion:
            texto_secundario = (getattr(persona.institucion, 'nombre', '') or '').strip().upper()
    except Exception:
        pass
    fs2 = 13
    while fs2 > 8 and stringWidth(texto_secundario, 'Helvetica-Bold', fs2) > max_w:
        fs2 -= 0.5
    canvas.setFillColor(SENA_VERDE_OSCURO)
    canvas.setFont('Helvetica-Bold', fs2)
    canvas.drawCentredString(page_w / 2, page_h * 0.38, texto_secundario)

    # Documento
    doc_texto = f'Doc: {getattr(persona, "numero_identificacion", "") or ""}'
    canvas.setFillColor(SENA_AZUL)
    canvas.setFont('Helvetica', 7)
    canvas.drawString(10 * mm, 10 * mm, doc_texto)

    # QR
    qr_token = getattr(persona, 'qr_token', None)
    qr_size = 24 * mm
    qr_x = page_w - qr_size - 10 * mm
    qr_y = 10 * mm
    if qr_token:
        try:
            from reportlab.graphics.barcode.qr import QrCodeWidget
            from reportlab.graphics.shapes import Drawing
            qrw = QrCodeWidget(str(qr_token), barLevel='M', barWidth=qr_size, barHeight=qr_size)
            d = Drawing(qr_size, qr_size)
            d.add(qrw)
            d.drawOn(canvas, qr_x, qr_y)
        except Exception:
            pass
    canvas.setFillColor(HexColor('#555555'))
    canvas.setFont('Helvetica', 6)
    canvas.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, 'Escanea para verificar')


# =======================================================================
# CERTIFICADOS POR PROYECTO — Media carta (2 por hoja carta)
# Usa la imagen 'Certificado FERIA SENA.png' como fondo y superpone
# el nombre del proyecto, la institución y el QR.
# =======================================================================


def _draw_certificado_proyecto(canvas, x, y, w, h, proyecto, evento=None, qr_token=None):
    """Dibuja un certificado usando la imagen de fondo y superponiendo datos dinámicos.
    El área (w, h) es media carta (612x396), mismo ratio que la imagen de fondo."""
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth

    SENA_VERDE_OSCURO = HexColor('#1B5E20')
    SENA_AZUL = HexColor('#0D47A1')

    # --- Imagen de fondo (llena TODO el área media carta) ---
    if os.path.isfile(_CERT_FONDO_PATH):
        try:
            # Ratio imagen = 1.5451, ratio media carta = 1.5454 -> sin distorsión
            canvas.drawImage(_CERT_FONDO_PATH, x, y, width=w, height=h,
                             preserveAspectRatio=False, anchor='c')
        except Exception:
            pass

    # --- Nombre del proyecto (entre 'SE OTORGA AL PROYECTO' y 'DE LA INSTITUCIÓN EDUCATIVA') ---
    nombre_proy = (getattr(proyecto, 'nombre', '') or '').strip().upper()
    max_w = w - 50 * mm
    fs = 16
    while fs > 10 and stringWidth(nombre_proy, 'Helvetica-Bold', fs) > max_w:
        fs -= 0.5
    canvas.setFillColor(black)
    canvas.setFont('Helvetica-Bold', fs)
    # Posición: línea base ~50% desde abajo (centro del espacio entre las dos líneas de la plantilla)
    proy_y = y + h * 0.53
    canvas.drawCentredString(x + w / 2, proy_y, nombre_proy)

    # --- Nombre de la institución (entre 'DE LA INSTITUCIÓN EDUCATIVA' y el párrafo) ---
    nombre_inst = ''
    try:
        if getattr(proyecto, 'institucion_id', None) and proyecto.institucion:
            nombre_inst = (getattr(proyecto.institucion, 'nombre', '') or '').strip().upper()
    except Exception:
        pass
    fs2 = 11
    while fs2 > 8 and stringWidth(nombre_inst, 'Helvetica-Bold', fs2) > max_w:
        fs2 -= 0.5
    canvas.setFillColor(SENA_VERDE_OSCURO)
    canvas.setFont('Helvetica-Bold', fs2)
    # Posición: línea base ~45% desde abajo (justo debajo de 'DE LA INSTITUCIÓN EDUCATIVA')
    inst_y = y + h * 0.45
    canvas.drawCentredString(x + w / 2, inst_y, nombre_inst)

    # --- Código del proyecto (esquina inferior izquierda, dentro de la imagen) ---
    cod_texto = f'Cód: {getattr(proyecto, "codigo", "") or ""}'
    cod_fs = 7
    canvas.setFont('Helvetica', cod_fs)
    cod_w = stringWidth(cod_texto, 'Helvetica', cod_fs)
    cod_x = x + 8 * mm
    cod_y = y + 4 * mm
    # Fondo blanco semi-transparente para legibilidad sobre el paisaje
    canvas.setFillColor(HexColor('#FFFFFFCC'))
    canvas.rect(cod_x - 1 * mm, cod_y - 1 * mm, cod_w + 2 * mm, cod_fs * 0.5 + 2 * mm,
                stroke=0, fill=1)
    canvas.setFillColor(SENA_AZUL)
    canvas.drawString(cod_x, cod_y, cod_texto)

    # --- QR (esquina inferior derecha, dentro de la imagen) ---
    qr_size = 22 * mm
    qr_x = x + w - qr_size - 10 * mm
    qr_y = y + 4 * mm
    if qr_token:
        try:
            from reportlab.graphics.barcode.qr import QrCodeWidget
            from reportlab.graphics.shapes import Drawing
            # Fondo blanco detrás del QR para legibilidad
            canvas.setFillColor(white)
            canvas.rect(qr_x - 1 * mm, qr_y - 1 * mm, qr_size + 2 * mm, qr_size + 2 * mm,
                        stroke=0, fill=1)
            qrw = QrCodeWidget(str(qr_token), barLevel='M', barWidth=qr_size, barHeight=qr_size)
            d = Drawing(qr_size, qr_size)
            d.add(qrw)
            d.drawOn(canvas, qr_x, qr_y)
        except Exception:
            pass


def generar_certificados_proyectos_pdf(proyectos, evento=None, buffer=None):
    """Genera un PDF con certificados de proyectos, 2 por hoja carta (media carta).
    El QR de cada certificado es el token_verificacion del CertificadoProyecto."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as canvas_mod

    if buffer is None:
        buffer = BytesIO()

    page_w, page_h = letter  # 612 x 792 pt = 215.9 x 279.4 mm
    cert_w = page_w
    cert_h = page_h / 2  # media carta = 396 pt = 139.7 mm

    c = canvas_mod.Canvas(buffer, pagesize=letter)

    # Obtener los tokens de certificado de todos los proyectos en una sola consulta
    proyecto_ids = [p.id for p in proyectos]
    tokens_por_proyecto = {}
    try:
        from apps.certificados.models import CertificadoProyecto
        tokens_por_proyecto = dict(
            CertificadoProyecto.objects.filter(proyecto_id__in=proyecto_ids)
            .values_list('proyecto_id', 'token_verificacion')
        )
    except Exception:
        # Fallback si la tabla no existe en la base de datos (evita error 500)
        pass

    for idx, proyecto in enumerate(proyectos):
        # Obtener el token del certificado de este proyecto
        qr_token = tokens_por_proyecto.get(proyecto.id)
        if not qr_token:
            # Fallback al código del proyecto si no hay token (por tabla faltante o no generado)
            qr_token = proyecto.codigo or f"PROY-{proyecto.id}"

        # Posición: par = arriba, impar = abajo
        pos_in_page = idx % 2
        if pos_in_page == 0:
            x, y = 0, cert_h  # certificado superior
        else:
            x, y = 0, 0  # certificado inferior

        _draw_certificado_proyecto(c, x, y, cert_w, cert_h, proyecto, evento=evento, qr_token=qr_token)

        # Si es el segundo de la página (impar), pasar de página
        if pos_in_page == 1 and idx < len(proyectos) - 1:
            c.showPage()

    # Si el último quedó solo (posición 0), asegurarse de mostrar la página
    if len(proyectos) % 2 == 1:
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer
