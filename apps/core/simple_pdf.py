import os
from io import BytesIO
from pathlib import Path

from django.http import HttpResponse
from django.conf import settings

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
# ESCARAPELA INDIVIDUAL A6 HORIZONTAL
#  - LOGO SENA: CENTRADO (arriba)
#  - QR:        CENTRADO (abajo)
# =======================================================================
def generar_escarapela_individual(persona, evento=None, proyecto=None, buffer=None):
    if buffer is None:
        buffer = BytesIO()

    page_w, page_h = landscape(A6)
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A6),
                              leftMargin=4*mm, rightMargin=4*mm,
                              topMargin=3*mm, bottomMargin=3*mm)
    styles = _estilos()
    story = []

    page_w_usable = page_w - 8*mm  # márgenes 4mm lados

    # ===========================================================
    # FRanja superior: LOGO CENTRADO (institucional) + datos evento
    # ===========================================================
    logo_centrado = _construir_logo_centrado(styles, ancho_mm=26, alto_mm=26)
    evento_titulo = Paragraph(
        f'<b>{evento.nombre}</b>' if evento else '<b>Feria Proyectos Productivos SENA</b>',
        styles['SenaSubtitulo']
    )
    if evento:
        partes_meta = []
        for val in [evento.lugar, evento.municipio]:
            if val:
                partes_meta.append(str(val))
        fechas = ''
        if evento.fecha_inicio or evento.fecha_fin:
            fi = str(evento.fecha_inicio) if evento.fecha_inicio else ''
            ff = str(evento.fecha_fin) if evento.fecha_fin else ''
            fechas = (f'{fi} - {ff}' if (fi and ff) else (fi or ff))
        if fechas:
            partes_meta.append(fechas)
        meta_text = ' · '.join(partes_meta) or ' '
    else:
        meta_text = ' '
    evento_meta = Paragraph(meta_text, styles['SenaInfo'])
    cabecera_centrada = [
        logo_centrado,
        Spacer(1, 1.5*mm),
        evento_titulo,
        evento_meta,
    ]
    cab_tbl = Table([[cabecera_centrada]], colWidths=[page_w_usable])
    cab_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SENA_VERDE),
        ('TEXTCOLOR', (0, 0), (-1, -1), white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(cab_tbl)
    story.append(Spacer(1, 3*mm))

    # ===========================================================
    # Cuerpo central: Nombre CENTRADO + Rol + Info Proyecto
    # ===========================================================
    nombre = persona.get_full_name()
    rol_nice = {'APRENDIZ': 'Aprendiz', 'INSTRUCTOR': 'Instructor',
                'INVITADO': 'Invitado', 'ACUDIENTE': 'Acudiente'}.get(persona.tipo_persona or '', 'Participante')
    color_rol = {'APRENDIZ': SENA_VERDE, 'INSTRUCTOR': SENA_AZUL,
                 'INVITADO': SENA_NARANJA, 'ACUDIENTE': SENA_GRIS}.get(persona.tipo_persona or '', SENA_GRIS)

    info_piezas = []
    if proyecto:
        info_piezas.append(f'<b>Proyecto:</b> {proyecto.nombre}')
    elif persona.tipo_persona == 'APRENDIZ':
        try:
            if hasattr(persona, 'perfil_aprendiz') and persona.perfil_aprendiz and persona.perfil_aprendiz.proyecto:
                info_piezas.append(f'<b>Proyecto:</b> {persona.perfil_aprendiz.proyecto.nombre}')
        except Exception:
            pass
    if evento and evento.municipio:
        info_piezas.append(f'<b>Municipio:</b> {evento.municipio}')
    if persona.correo:
        info_piezas.append(f'<b>Correo:</b> {persona.correo[:38]}')
    info_html = '<br/>'.join(info_piezas) or ' '

    story.append(Paragraph(nombre.upper(), styles['SenaNombre']))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(rol_nice.upper(),
                 ParagraphStyle(name='_r_esc', textColor=color_rol, fontName='Helvetica-Bold',
                                fontSize=10, leading=12, alignment=1)))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(info_html, styles['SenaInfo']))
    story.append(Spacer(1, 3*mm))

    # ===========================================================
    # QR CENTRADO (abajo) + leyenda ID
    # ===========================================================
    qr_dibujo = _dibujar_qr_bytes(str(persona.qr_token), tamano_mm=28)
    leyenda_qr = Paragraph(f'<b>ID:</b> {str(persona.qr_token)[:16]}', styles['SenaChico'])
    qr_bloque_centrado = Table(
        [[qr_dibujo], [leyenda_qr]],
        colWidths=[28*mm],
        rowHeights=[28*mm, None]
    )
    qr_bloque_centrado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    qr_container_tbl = Table([[qr_bloque_centrado]], colWidths=[page_w_usable])
    qr_container_tbl.setStyle(TableStyle([
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), SENA_BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(qr_container_tbl)
    story.append(Spacer(1, 2*mm))

    # Pie
    pie = Paragraph('<b>SENA · Regional Guajira · Feria de Proyectos Productivos · Valido solo con documento de identidad</b>', styles['SenaInfo'])
    story.append(pie)

    doc.build(story)
    return buffer


def generar_escarapelas_lote(lista_personas, evento=None, nombre_archivo='escarapelas.pdf'):
    buffer = BytesIO()
    page_w, page_h = landscape(A6)
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A6),
                              leftMargin=4*mm, rightMargin=4*mm,
                              topMargin=3*mm, bottomMargin=3*mm,
                              title=nombre_archivo)
    styles = _estilos()
    story = []

    logo_centrado = _construir_logo_centrado(styles, ancho_mm=26, alto_mm=26)
    page_w_usable = page_w - 8*mm

    for idx, item in enumerate(lista_personas):
        if isinstance(item, tuple):
            persona, proyecto = item
        else:
            persona, proyecto = item, None

        if idx > 0:
            story.append(PageBreak())

        evento_titulo = Paragraph(
            f'<b>{evento.nombre}</b>' if evento else '<b>Feria Proyectos Productivos SENA</b>',
            styles['SenaSubtitulo']
        )
        if evento:
            partes_meta = []
            for val in [evento.lugar, evento.municipio]:
                if val:
                    partes_meta.append(str(val))
            fechas = ''
            if evento.fecha_inicio or evento.fecha_fin:
                fi = str(evento.fecha_inicio) if evento.fecha_inicio else ''
                ff = str(evento.fecha_fin) if evento.fecha_fin else ''
                fechas = (f'{fi} - {ff}' if (fi and ff) else (fi or ff))
            if fechas:
                partes_meta.append(fechas)
            meta_text = ' · '.join(partes_meta) or ' '
        else:
            meta_text = ' '
        evento_meta = Paragraph(meta_text, styles['SenaInfo'])
        cabecera_centrada = [logo_centrado, Spacer(1, 1.5*mm), evento_titulo, evento_meta]
        cab_tbl = Table([[cabecera_centrada]], colWidths=[page_w_usable])
        cab_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), SENA_VERDE),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(cab_tbl)
        story.append(Spacer(1, 3*mm))

        nombre = persona.get_full_name()
        rol_nice = {'APRENDIZ': 'Aprendiz', 'INSTRUCTOR': 'Instructor',
                    'INVITADO': 'Invitado', 'ACUDIENTE': 'Acudiente'}.get(persona.tipo_persona or '', 'Participante')
        color_rol = {'APRENDIZ': SENA_VERDE, 'INSTRUCTOR': SENA_AZUL,
                     'INVITADO': SENA_NARANJA, 'ACUDIENTE': SENA_GRIS}.get(persona.tipo_persona or '', SENA_GRIS)

        info_piezas = []
        if proyecto:
            info_piezas.append(f'<b>Proyecto:</b> {proyecto.nombre[:55]}')
        elif persona.tipo_persona == 'APRENDIZ':
            try:
                if hasattr(persona, 'perfil_aprendiz') and persona.perfil_aprendiz and persona.perfil_aprendiz.proyecto:
                    info_piezas.append(f'<b>Proyecto:</b> {persona.perfil_aprendiz.proyecto.nombre[:55]}')
            except Exception:
                pass
        if evento and evento.municipio:
            info_piezas.append(f'<b>Municipio:</b> {evento.municipio}')
        if persona.correo:
            info_piezas.append(f'<b>Correo:</b> {persona.correo[:38]}')
        info_html = '<br/>'.join(info_piezas) or ' '

        story.append(Paragraph(nombre.upper(), styles['SenaNombre']))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(rol_nice.upper(),
                     ParagraphStyle(name='_r_lote' + str(idx), textColor=color_rol,
                                    fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=1)))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(info_html, styles['SenaInfo']))
        story.append(Spacer(1, 3*mm))

        qr_dibujo = _dibujar_qr_bytes(str(persona.qr_token), tamano_mm=28)
        leyenda_qr = Paragraph(f'<b>ID:</b> {str(persona.qr_token)[:16]}', styles['SenaChico'])
        qr_bloque_centrado = Table(
            [[qr_dibujo], [leyenda_qr]],
            colWidths=[28*mm],
            rowHeights=[28*mm, None]
        )
        qr_bloque_centrado.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        qr_container_tbl = Table([[qr_bloque_centrado]], colWidths=[page_w_usable])
        qr_container_tbl.setStyle(TableStyle([
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), SENA_BG_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        story.append(qr_container_tbl)
        story.append(Spacer(1, 2*mm))

        pie = Paragraph('<b>SENA · Regional Guajira · Feria de Proyectos Productivos · Valido solo con documento de identidad</b>', styles['SenaInfo'])
        story.append(pie)

    doc.build(story)
    return buffer


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
                'INVITADO': 'Invitado', 'ACUDIENTE': 'Acudiente'}.get(persona.tipo_persona or '', 'Participante')
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
    tipo = (tipo or 'ASISTENCIA').upper()
    plantilla = PLANTILLAS_CERTIFICADO.get(tipo, PLANTILLAS_CERTIFICADO['ASISTENCIA'])
    vars_ = _reemplazar_plantilla(plantilla, persona, evento=evento, proyecto=proyecto, overrides=overrides)
    if buffer is None:
        buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=18*mm, title=f'{tipo}_{persona.numero_identificacion or persona.id}.pdf')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TituloCert', textColor=SENA_VERDE, fontName='Helvetica-Bold', fontSize=20, leading=26, alignment=1, spaceAfter=10))
    styles.add(ParagraphStyle(name='IntroCert', textColor=SENA_GRIS, fontName='Helvetica', fontSize=11, leading=16, alignment=1, spaceAfter=14))
    styles.add(ParagraphStyle(name='CentralCert', textColor=black, fontName='Helvetica', fontSize=13, leading=20, alignment=4, spaceAfter=16, spaceBefore=6))
    styles.add(ParagraphStyle(name='FinalCert', textColor=SENA_GRIS, fontName='Helvetica', fontSize=11, leading=16, alignment=4, spaceAfter=22))
    styles.add(ParagraphStyle(name='FirmaNombre', textColor=SENA_AZUL, fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=1))
    styles.add(ParagraphStyle(name='FirmaCargo', textColor=SENA_GRIS, fontName='Helvetica', fontSize=9, leading=11, alignment=1))

    usable_w = 170 * mm  # A4 usable aprox 210 - 2*20 márgenes

    story = []
    # ===========================================================
    # Cabecera institucional: LOGO SENA CENTRADO (arriba)
    # ===========================================================
    logo_centrado = _construir_logo_centrado(styles, ancho_mm=32, alto_mm=32)
    sena_titulo = Paragraph('<b>SERVICIO NACIONAL DE APRENDIZAJE - SENA</b>',
                 ParagraphStyle(name='C1_cert', textColor=SENA_AZUL, fontName='Helvetica-Bold',
                                alignment=1, leading=15, fontSize=13))
    sena_sub = Paragraph('<b>Regional Guajira · Feria de Proyectos Productivos</b>',
                ParagraphStyle(name='C2_cert', textColor=SENA_VERDE, fontName='Helvetica',
                               alignment=1, leading=12, fontSize=10))
    cabecera_centrada = [
        logo_centrado,
        Spacer(1, 2*mm),
        sena_titulo,
        sena_sub,
    ]
    cab = Table([[cabecera_centrada]], colWidths=[usable_w])
    cab.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 2, SENA_VERDE),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
    ]))
    story.append(cab)
    story.append(Spacer(1, 10*mm))

    story.append(Paragraph(plantilla['titulo'], styles['TituloCert']))
    story.append(Paragraph('__________________________________________________', ParagraphStyle(name='sep', alignment=1, textColor=SENA_VERDE, fontName='Helvetica')))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph(plantilla['parrafo_intro'].format(**vars_), styles['IntroCert']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(plantilla['parrafo_central'].format(**vars_), styles['CentralCert']))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(plantilla['parrafo_final'].format(**vars_), styles['FinalCert']))
    story.append(Spacer(1, 14*mm))

    # Firmas
    col_f1 = [
        Paragraph('_' * 40, styles['FirmaNombre']),
        Spacer(1, 1*mm),
        Paragraph(vars_['FIRMA_1_NOMBRE'], styles['FirmaNombre']),
        Paragraph(vars_['FIRMA_1_CARGO'], styles['FirmaCargo']),
    ]
    col_f2 = [
        Paragraph('_' * 40, styles['FirmaNombre']),
        Spacer(1, 1*mm),
        Paragraph(vars_['FIRMA_2_NOMBRE'], styles['FirmaNombre']),
        Paragraph(vars_['FIRMA_2_CARGO'], styles['FirmaCargo']),
    ]
    firmas = Table([[col_f1, col_f2]], colWidths=[80*mm, 80*mm])
    firmas.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(firmas)
    story.append(Spacer(1, 10*mm))

    # ===========================================================
    # QR CENTRADO (abajo) con ID / validez
    # ===========================================================
    qr_dibujo = _dibujar_qr_bytes(str(persona.qr_token), tamano_mm=26)
    leyenda_qr = Paragraph(
        f'<b>Certificación digital SENA · ID:</b> {str(persona.qr_token)[:20]}<br/>'
        f'<font color="#555555">Valide públicamente en el sistema de la feria</font>',
        ParagraphStyle(name='qr_ley', textColor=SENA_VERDE, fontName='Helvetica',
                       fontSize=8, leading=10, alignment=1)
    )
    qr_bloque_centrado = Table(
        [[qr_dibujo], [leyenda_qr]],
        colWidths=[26*mm],
        rowHeights=[26*mm, None]
    )
    qr_bloque_centrado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    qr_container_tbl = Table([[qr_bloque_centrado]], colWidths=[usable_w])
    qr_container_tbl.setStyle(TableStyle([
        ('ALIGN',     (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND',(0, 0), (-1, -1), SENA_BG_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(qr_container_tbl)

    doc.build(story)
    return buffer


def generar_certificados_lote(lista, tipo='ASISTENCIA', evento=None):
    buffer = BytesIO()
    from reportlab.lib.pagesizes import A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=18*mm, title=f'{tipo}_LOTE.pdf')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TituloCert2', textColor=SENA_VERDE, fontName='Helvetica-Bold', fontSize=20, leading=26, alignment=1, spaceAfter=10))
    styles.add(ParagraphStyle(name='IntroCert2', textColor=SENA_GRIS, fontName='Helvetica', fontSize=11, leading=16, alignment=1, spaceAfter=14))
    styles.add(ParagraphStyle(name='CentralCert2', textColor=black, fontName='Helvetica', fontSize=13, leading=20, alignment=4, spaceAfter=16, spaceBefore=6))
    styles.add(ParagraphStyle(name='FinalCert2', textColor=SENA_GRIS, fontName='Helvetica', fontSize=11, leading=16, alignment=4, spaceAfter=22))
    styles.add(ParagraphStyle(name='FirmaNombre2', textColor=SENA_AZUL, fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=1))
    styles.add(ParagraphStyle(name='FirmaCargo2', textColor=SENA_GRIS, fontName='Helvetica', fontSize=9, leading=11, alignment=1))

    usable_w = 170 * mm
    logo_centrado = _construir_logo_centrado(styles, ancho_mm=32, alto_mm=32)

    tipo = (tipo or 'ASISTENCIA').upper()
    plantilla = PLANTILLAS_CERTIFICADO.get(tipo, PLANTILLAS_CERTIFICADO['ASISTENCIA'])

    for idx, item in enumerate(lista):
        if isinstance(item, tuple):
            persona, proyecto = item
        else:
            persona, proyecto = item, None
        if idx > 0:
            story.append(PageBreak())

        story = [] if idx == 0 else story

        vars_ = _reemplazar_plantilla(plantilla, persona, evento=evento, proyecto=proyecto)
        sena_titulo = Paragraph('<b>SERVICIO NACIONAL DE APRENDIZAJE - SENA</b>',
                     ParagraphStyle(name='C1p'+str(idx), textColor=SENA_AZUL, fontName='Helvetica-Bold',
                                    alignment=1, leading=15, fontSize=13))
        sena_sub = Paragraph('<b>Regional Guajira · Feria de Proyectos Productivos</b>',
                    ParagraphStyle(name='C2p'+str(idx), textColor=SENA_VERDE, fontName='Helvetica',
                                   alignment=1, leading=12, fontSize=10))
        cabecera_centrada = [logo_centrado, Spacer(1, 2*mm), sena_titulo, sena_sub]
        cab = Table([[cabecera_centrada]], colWidths=[usable_w])
        cab.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('LINEBELOW', (0, 0), (-1, -1), 2, SENA_VERDE),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ]))
        story.append(cab)
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph(plantilla['titulo'], styles['TituloCert2']))
        story.append(Paragraph('__________________________________________________', ParagraphStyle(name='sep2'+str(idx), alignment=1, textColor=SENA_VERDE, fontName='Helvetica')))
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(plantilla['parrafo_intro'].format(**vars_), styles['IntroCert2']))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(plantilla['parrafo_central'].format(**vars_), styles['CentralCert2']))
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph(plantilla['parrafo_final'].format(**vars_), styles['FinalCert2']))
        story.append(Spacer(1, 14*mm))
        col_f1 = [
            Paragraph('_' * 40, styles['FirmaNombre2']),
            Spacer(1, 1*mm),
            Paragraph(vars_['FIRMA_1_NOMBRE'], styles['FirmaNombre2']),
            Paragraph(vars_['FIRMA_1_CARGO'], styles['FirmaCargo2']),
        ]
        col_f2 = [
            Paragraph('_' * 40, styles['FirmaNombre2']),
            Spacer(1, 1*mm),
            Paragraph(vars_['FIRMA_2_NOMBRE'], styles['FirmaNombre2']),
            Paragraph(vars_['FIRMA_2_CARGO'], styles['FirmaCargo2']),
        ]
        firmas = Table([[col_f1, col_f2]], colWidths=[80*mm, 80*mm])
        firmas.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        story.append(firmas)
        story.append(Spacer(1, 10*mm))

        qr_dibujo = _dibujar_qr_bytes(str(persona.qr_token), tamano_mm=26)
        leyenda_qr = Paragraph(
            f'<b>Certificación digital SENA · ID:</b> {str(persona.qr_token)[:20]}<br/>'
            f'<font color="#555555">Valide públicamente en el sistema de la feria</font>',
            ParagraphStyle(name='qr_ley'+str(idx), textColor=SENA_VERDE, fontName='Helvetica',
                           fontSize=8, leading=10, alignment=1)
        )
        qr_bloque_centrado = Table(
            [[qr_dibujo], [leyenda_qr]],
            colWidths=[26*mm],
            rowHeights=[26*mm, None]
        )
        qr_bloque_centrado.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        qr_container_tbl = Table([[qr_bloque_centrado]], colWidths=[usable_w])
        qr_container_tbl.setStyle(TableStyle([
            ('ALIGN',     (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND',(0, 0), (-1, -1), SENA_BG_LIGHT),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        story.append(qr_container_tbl)

    doc.build(story)
    return buffer
