import io
from pathlib import Path

from django.conf import settings

from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from apps.personas.services import QrService


A6 = (148 * mm, 105 * mm)

COLOR_SENA_VERDE = HexColor('#39A900')
COLOR_SENA_VERDE_OSCURO = HexColor('#2E7F00')
COLOR_SENA_AZUL = HexColor('#0067B1')
COLOR_INVITADO_NARANJA = HexColor('#F57C00')
COLOR_ORGANIZADOR_MORADO = HexColor('#7B1FA2')
COLOR_GRIS_FONDO = HexColor('#F5F7F0')
COLOR_GRIS_TEXTO = HexColor('#555555')
COLOR_GRIS_BORDE = HexColor('#D8E0CC')

COLORES_ROL = {
    'APRENDIZ': COLOR_SENA_VERDE,
    'INSTRUCTOR': COLOR_SENA_AZUL,
    'INVITADO': COLOR_INVITADO_NARANJA,
    'ORGANIZADOR': COLOR_ORGANIZADOR_MORADO,
}

ETIQUETAS_ROL = {
    'APRENDIZ': 'APRENDIZ',
    'INSTRUCTOR': 'INSTRUCTOR',
    'INVITADO': 'INVITADO ESPECIAL',
    'ORGANIZADOR': 'ORGANIZADOR',
}


class EscarapelaPDFService:
    PAGE_W, PAGE_H = landscape(A6)
    MARGEN = 6 * mm

    @staticmethod
    def _ruta_logo_sena():
        static_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / 'static']
        return Path(static_dirs[0]) / 'img' / 'logo-sena-verde.png'

    @staticmethod
    def _info_persona(persona):
        info = {
            'institucion': None,
            'programa': None,
            'proyecto': None,
            'extra': None,
            'codigo_ficha': None,
            'tipo_identificacion': None,
            'numero_identificacion': None,
        }

        try:
            if persona.tipo_identificacion:
                info['tipo_identificacion'] = (persona.tipo_identificacion.abreviatura or '').upper()
        except Exception:
            pass
        info['numero_identificacion'] = persona.numero_identificacion or ''

        if persona.tipo_persona == 'APRENDIZ':
            perfil = getattr(persona, 'perfil_aprendiz', None)
            if perfil and perfil.proyecto:
                info['proyecto'] = perfil.proyecto.nombre
                if perfil.proyecto.institucion:
                    info['institucion'] = perfil.proyecto.institucion.nombre
                if perfil.proyecto.programa:
                    info['programa'] = perfil.proyecto.programa.nombre
                if perfil.proyecto.ficha:
                    info['codigo_ficha'] = perfil.proyecto.ficha.numero
        elif persona.tipo_persona == 'INSTRUCTOR':
            perfil = getattr(persona, 'perfil_instructor', None)
            if perfil:
                programas = list(perfil.programas.all()[:2])
                if programas:
                    info['programa'] = ' · '.join(p.nombre for p in programas)
                info['extra'] = 'Instructor SENA'
        elif persona.tipo_persona == 'INVITADO':
            perfil = getattr(persona, 'perfil_invitado', None)
            if perfil:
                info['institucion'] = perfil.entidad
                info['extra'] = perfil.cargo

        return info

    @staticmethod
    def _centrar_texto(c, texto, y, fuente, tamano, color=None, max_w=None):
        if color is None:
            color = black
        if max_w is None:
            max_w = EscarapelaPDFService.PAGE_W - 2 * EscarapelaPDFService.MARGEN
        ancho = c.stringWidth(texto, fuente, tamano)
        if ancho > max_w and tamano > 7:
            return EscarapelaPDFService._centrar_texto(c, texto, y, fuente, tamano - 1, color, max_w)
        c.setFillColor(color)
        c.setFont(fuente, tamano)
        x = (EscarapelaPDFService.PAGE_W - ancho) / 2
        c.drawString(x, y, texto)
        return x, y, ancho

    @staticmethod
    def _dibujar_logo(c, y_centro, alto_logo):
        ruta_logo = EscarapelaPDFService._ruta_logo_sena()
        if not ruta_logo.exists():
            return
        try:
            from PIL import Image
            with Image.open(ruta_logo) as img:
                w_img, h_img = img.size
                ratio = alto_logo / h_img
                ancho_logo = w_img * ratio
            x_logo = (EscarapelaPDFService.PAGE_W - ancho_logo) / 2
            y_logo = y_centro - alto_logo / 2
            c.drawImage(
                str(ruta_logo),
                x_logo,
                y_logo,
                width=ancho_logo,
                height=alto_logo,
                mask='auto',
            )
        except Exception:
            pass

    @staticmethod
    def _dibujar_badge_centrado(c, y_inf, ancho, alto, radio, color_fondo, texto, color_texto, fuente, tamano):
        x = (EscarapelaPDFService.PAGE_W - ancho) / 2
        c.setFillColor(color_fondo)
        c.roundRect(x, y_inf, ancho, alto, radio, fill=1, stroke=0)
        EscarapelaPDFService._centrar_texto(
            c, texto, y_inf + alto / 2 - (tamano * 0.35), fuente, tamano, color_texto, ancho - 4 * mm
        )

    @staticmethod
    def _dibujar_franja_inferior(c, evento, color_fondo, color_texto, alto_banda=10 * mm):
        c.setFillColor(color_fondo)
        c.rect(0, 0, EscarapelaPDFService.PAGE_W, alto_banda, fill=1, stroke=0)
        evento_nombre = (evento.nombre if evento else 'Evento').strip()
        fecha_txt = ''
        try:
            if evento and evento.fecha_inicio and evento.fecha_fin:
                fecha_txt = f' · {evento.fecha_inicio.strftime("%d/%m/%Y")} - {evento.fecha_fin.strftime("%d/%m/%Y")}'
            elif evento and evento.fecha_inicio:
                fecha_txt = f' · {evento.fecha_inicio.strftime("%d/%m/%Y")}'
        except Exception:
            pass
        sede_txt = ''
        try:
            if evento and evento.lugar:
                sede_txt = f' · {evento.lugar}'
        except Exception:
            pass
        pie = f'SENA  |  {evento_nombre}{sede_txt}{fecha_txt}'
        if len(pie) > 140:
            pie = pie[:137] + '...'
        EscarapelaPDFService._centrar_texto(c, pie, alto_banda / 2 - 2.6 * mm, 'Helvetica', 7.4, color_texto)

    @staticmethod
    def _dibujar_frente(c, persona, evento):
        # Fondo general suave
        c.setFillColor(COLOR_GRIS_FONDO)
        c.rect(0, 0, EscarapelaPDFService.PAGE_W, EscarapelaPDFService.PAGE_H, fill=1, stroke=0)

        # --- BANDA SUPERIOR VERDE (ALTA, 40mm) ---
        banda_alto = 40 * mm
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(0, EscarapelaPDFService.PAGE_H - banda_alto, EscarapelaPDFService.PAGE_W, banda_alto, fill=1, stroke=0)
        # Linea inferior sutil en la banda
        c.setFillColor(COLOR_SENA_VERDE_OSCURO)
        c.rect(0, EscarapelaPDFService.PAGE_H - banda_alto, EscarapelaPDFService.PAGE_W, 0.8 * mm, fill=1, stroke=0)

        # Logo SENA CENTRADO dentro de la banda verde
        logo_alto = 26 * mm
        EscarapelaPDFService._dibujar_logo(c, EscarapelaPDFService.PAGE_H - banda_alto / 2 - 1 * mm, logo_alto)

        # Nombre evento (centrado, blanco, sobre fondo verde, debajo de logo)
        evento_y = EscarapelaPDFService.PAGE_H - banda_alto + 7 * mm
        evento_nombre = (evento.nombre if evento else 'Evento').upper()
        EscarapelaPDFService._centrar_texto(c, evento_nombre, evento_y, 'Helvetica-Bold', 10.5, white,
                                            EscarapelaPDFService.PAGE_W - 14 * mm)

        # --- ZONA INFERIOR (Datos persona) ---
        # 1) BADGE ROL (centrado, color)
        color_rol = COLORES_ROL.get(persona.tipo_persona, COLOR_SENA_VERDE)
        etiqueta_rol = ETIQUETAS_ROL.get(persona.tipo_persona, persona.tipo_persona or '')
        badge_alto = 12 * mm
        badge_ancho = 64 * mm
        badge_y = EscarapelaPDFService.PAGE_H - banda_alto - 18 * mm
        EscarapelaPDFService._dibujar_badge_centrado(
            c, badge_y, badge_ancho, badge_alto, 3.2 * mm, color_rol, etiqueta_rol,
            white, 'Helvetica-Bold', 11.5,
        )

        # 2) NOMBRE COMPLETO PERSONA (muy grande, mayúsculas, CENTRADO)
        nombre_y = badge_y - 10 * mm
        nombre_texto = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar_texto(c, nombre_texto, nombre_y, 'Helvetica-Bold', 18, black,
                                            EscarapelaPDFService.PAGE_W - 16 * mm)

        # 3) CAJA TIPO DOC + NUMERO DOC (centrada, gris)
        info = EscarapelaPDFService._info_persona(persona)
        caja_doc_alto = 11 * mm
        caja_doc_ancho = 78 * mm
        caja_doc_y = nombre_y - 16 * mm
        c.setStrokeColor(COLOR_GRIS_BORDE)
        c.setFillColor(white)
        c.roundRect(
            (EscarapelaPDFService.PAGE_W - caja_doc_ancho) / 2,
            caja_doc_y,
            caja_doc_ancho,
            caja_doc_alto,
            2.4 * mm,
            fill=1, stroke=1,
        )
        tipo_doc = (info['tipo_identificacion'] or 'CC') + ':'
        num_doc = info['numero_identificacion'] or ''
        doc_texto = f'  {tipo_doc}  {num_doc}'
        EscarapelaPDFService._centrar_texto(c, doc_texto, caja_doc_y + 3.2 * mm,
                                            'Helvetica-Bold', 11, COLOR_SENA_VERDE_OSCURO,
                                            caja_doc_ancho - 4 * mm)

        # 4) Detalles (Proyecto, Ficha, IE, Programa) centrados multilinea
        detalle_y = caja_doc_y - 6 * mm
        lineas_detalle = []
        if info['proyecto']:
            lineas_detalle.append(('Proyecto', info['proyecto']))
        if info['codigo_ficha']:
            lineas_detalle.append(('Ficha', info['codigo_ficha']))
        if info['programa']:
            lineas_detalle.append(('Programa', info['programa']))
        if info['institucion']:
            lineas_detalle.append(('Institución', info['institucion']))
        if info['extra'] and not (
            info['institucion'] or info['programa'] or info['proyecto'] or info['codigo_ficha']
        ):
            lineas_detalle.append(('', info['extra']))

        max_lineas = 4
        for etiqueta, valor in lineas_detalle[:max_lineas]:
            if detalle_y < 13 * mm:
                break
            txt = f'{etiqueta + ": " if etiqueta else ""}{valor}'
            EscarapelaPDFService._centrar_texto(c, txt, detalle_y, 'Helvetica', 7.8,
                                                COLOR_GRIS_TEXTO,
                                                EscarapelaPDFService.PAGE_W - 18 * mm)
            detalle_y -= 4 * mm

        # --- FRANJA INFERIOR FOOTER ---
        EscarapelaPDFService._dibujar_franja_inferior(c, evento, COLOR_SENA_VERDE, white, 9 * mm)

    @staticmethod
    def _dibujar_reverso(c, persona, evento):
        # Fondo blanco suave
        c.setFillColor(white)
        c.rect(0, 0, EscarapelaPDFService.PAGE_W, EscarapelaPDFService.PAGE_H, fill=1, stroke=0)

        # BANDA SUPERIOR REVERSO (verde, 18mm alto)
        banda_superior_alto = 18 * mm
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(0, EscarapelaPDFService.PAGE_H - banda_superior_alto, EscarapelaPDFService.PAGE_W,
               banda_superior_alto, fill=1, stroke=0)
        # Logo SENA pequeño, CENTRADO en la banda superior
        EscarapelaPDFService._dibujar_logo(c, EscarapelaPDFService.PAGE_H - banda_superior_alto / 2, 12 * mm)
        # Texto aclarativo arriba
        EscarapelaPDFService._centrar_texto(
            c, 'IDENTIFICACIÓN DIGITAL - CÓDIGO ÚNICO', EscarapelaPDFService.PAGE_H - 14 * mm,
            'Helvetica-Bold', 7.5, white, EscarapelaPDFService.PAGE_W - 14 * mm
        )

        # --- QR GRANDE + PERFECTAMENTE CENTRADO ---
        qr_size = 55 * mm
        qr_x = (EscarapelaPDFService.PAGE_W - qr_size) / 2
        qr_y = (EscarapelaPDFService.PAGE_H + 12 * mm) / 2 - qr_size / 2
        # Cuadro fondo del QR (borde verde, blanco interior)
        c.setStrokeColor(COLOR_SENA_VERDE)
        c.setFillColor(COLOR_GRIS_FONDO)
        margen_qr = 3 * mm
        c.roundRect(
            qr_x - margen_qr, qr_y - margen_qr,
            qr_size + 2 * margen_qr, qr_size + 2 * margen_qr,
            4 * mm, fill=1, stroke=1,
        )
        # QR interno
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        try:
            c.drawImage(
                ruta_qr,
                qr_x, qr_y,
                width=qr_size,
                height=qr_size,
                mask='auto',
            )
        except Exception:
            c.setStrokeColor(HexColor('#cccccc'))
            c.setFillColor(HexColor('#f5f5f5'))
            c.rect(qr_x, qr_y, qr_size, qr_size, fill=1, stroke=1)
            c.setFillColor(HexColor('#999999'))
            c.setFont('Helvetica', 8)
            c.drawCentredString(
                qr_x + qr_size / 2,
                qr_y + qr_size / 2,
                'QR no disponible',
            )

        # --- ID UUID (centrado debajo QR) ---
        uuid_texto = f'ID: {persona.qr_token}'
        id_caja_ancho = 90 * mm
        id_caja_alto = 7 * mm
        id_caja_y = qr_y - 11 * mm
        c.setStrokeColor(COLOR_GRIS_BORDE)
        c.setFillColor(HexColor('#FAFCF4'))
        c.roundRect(
            (EscarapelaPDFService.PAGE_W - id_caja_ancho) / 2,
            id_caja_y, id_caja_ancho, id_caja_alto, 2 * mm, fill=1, stroke=1,
        )
        EscarapelaPDFService._centrar_texto(c, uuid_texto, id_caja_y + 1.8 * mm,
                                            'Helvetica', 7, COLOR_SENA_VERDE_OSCURO,
                                            id_caja_ancho - 2 * mm)

        # --- Nombre y Rol al pie del reverso (coincidencia al cortar) ---
        nombre_y = id_caja_y - 12 * mm
        info = EscarapelaPDFService._info_persona(persona)
        color_rol = COLORES_ROL.get(persona.tipo_persona, COLOR_SENA_VERDE)
        nombre_texto = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar_texto(c, nombre_texto, nombre_y, 'Helvetica-Bold', 9.5, black,
                                            EscarapelaPDFService.PAGE_W - 18 * mm)
        rol_texto = ETIQUETAS_ROL.get(persona.tipo_persona, persona.tipo_persona or '')
        EscarapelaPDFService._centrar_texto(c, rol_texto, nombre_y - 5 * mm,
                                            'Helvetica-Bold', 8, color_rol,
                                            EscarapelaPDFService.PAGE_W - 18 * mm)

        # --- FRANJA INFERIOR REVERSO (VERDE, footer leyenda) ---
        footer_alto = 10 * mm
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(0, 0, EscarapelaPDFService.PAGE_W, footer_alto, fill=1, stroke=0)
        leyenda = 'VÁLIDO SOLO CON DOCUMENTO DE IDENTIDAD ORIGINAL · SENA · FERIA DE PROYECTOS'
        EscarapelaPDFService._centrar_texto(c, leyenda, 3 * mm,
                                            'Helvetica-Bold', 6.8, white,
                                            EscarapelaPDFService.PAGE_W - 14 * mm)

    @staticmethod
    def _renderizar_persona(c, persona, evento):
        # Página 1 = Frente (datos persona, nombre grande, badge rol, ficha, IE)
        EscarapelaPDFService._dibujar_frente(c, persona, evento)
        c.showPage()
        # Página 2 = Reverso (QR gigante centrado, ID UUID, leyenda)
        EscarapelaPDFService._dibujar_reverso(c, persona, evento)
        c.showPage()

    @staticmethod
    def generar_individual(persona, evento):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A6))
        EscarapelaPDFService._renderizar_persona(c, persona, evento)
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generar_lote(qs_personas, evento, titulo_lote=None):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A6))
        for persona in qs_personas:
            EscarapelaPDFService._renderizar_persona(c, persona, evento)
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generar_por_proyecto(proyecto):
        from apps.personas.models import Persona

        evento = proyecto.evento
        qs = Persona.objects.filter(
            perfil_aprendiz__proyecto=proyecto,
            activo=True,
        ).order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'Proyecto {proyecto.codigo}')

    @staticmethod
    def generar_por_institucion(ie, evento):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto

        proyectos_ie = Proyecto.objects.filter(institucion=ie, evento=evento).values_list('id', flat=True)
        qs = Persona.objects.filter(
            perfil_aprendiz__proyecto_id__in=list(proyectos_ie),
            activo=True,
        ).order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'Institución {ie.codigo}')

    @staticmethod
    def generar_por_programa(programa, evento):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto

        programas_p = Proyecto.objects.filter(programa=programa, evento=evento).values_list('id', flat=True)
        qs_aprendices = Persona.objects.filter(
            perfil_aprendiz__proyecto_id__in=list(programas_p),
            activo=True,
        )
        qs_instructores = Persona.objects.filter(
            perfil_instructor__programas=programa,
            activo=True,
        )
        qs = (qs_aprendices | qs_instructores).distinct().order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'Programa {programa.codigo}')

    @staticmethod
    def generar_completo(evento):
        from django.db.models import Q
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto

        proyectos_evento = list(Proyecto.objects.filter(evento=evento).values_list('id', flat=True))
        instructores_proyectos = list(
            Proyecto.objects.filter(evento=evento)
            .exclude(instructor_responsable__isnull=True)
            .values_list('instructor_responsable__persona_id', flat=True)
        )

        qs = Persona.objects.filter(
            activo=True,
        ).filter(
            Q(perfil_aprendiz__proyecto_id__in=proyectos_evento)
            | Q(id__in=instructores_proyectos)
            | Q(tipo_persona__in=['INVITADO', 'ORGANIZADOR'])
        ).distinct().order_by('tipo_persona', 'apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, 'Completo')
