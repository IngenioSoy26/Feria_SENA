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
COLOR_SENA_AZUL = HexColor('#0067B1')
COLOR_INVITADO_NARANJA = HexColor('#F57C00')
COLOR_ORGANIZADOR_MORADO = HexColor('#7B1FA2')

COLORES_ROL = {
    'APRENDIZ': COLOR_SENA_VERDE,
    'INSTRUCTOR': COLOR_SENA_AZUL,
    'INVITADO': COLOR_INVITADO_NARANJA,
    'ORGANIZADOR': COLOR_ORGANIZADOR_MORADO,
}

ETIQUETAS_ROL = {
    'APRENDIZ': 'APRENDIZ',
    'INSTRUCTOR': 'INSTRUCTOR',
    'INVITADO': 'INVITADO',
    'ORGANIZADOR': 'ORGANIZADOR',
}


class EscarapelaPDFService:
    PAGE_W, PAGE_H = landscape(A6)
    BANDA_ALTO = 28 * mm
    QR_SIZE = 35 * mm
    MARGEN = 8 * mm

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
        }

        if persona.tipo_persona == 'APRENDIZ':
            perfil = getattr(persona, 'perfil_aprendiz', None)
            if perfil and perfil.proyecto:
                info['proyecto'] = perfil.proyecto.nombre
                info['institucion'] = perfil.proyecto.institucion.nombre
                info['programa'] = perfil.proyecto.programa.nombre
        elif persona.tipo_persona == 'INSTRUCTOR':
            perfil = getattr(persona, 'perfil_instructor', None)
            if perfil:
                programas = list(perfil.programas.all()[:2])
                if programas:
                    info['programa'] = ' / '.join(p.codigo for p in programas)
        elif persona.tipo_persona == 'INVITADO':
            perfil = getattr(persona, 'perfil_invitado', None)
            if perfil:
                info['institucion'] = perfil.entidad
                info['extra'] = perfil.cargo

        return info

    @staticmethod
    def _dibujar_encabezado(c, evento):
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(0, EscarapelaPDFService.PAGE_H - EscarapelaPDFService.BANDA_ALTO,
               EscarapelaPDFService.PAGE_W, EscarapelaPDFService.BANDA_ALTO, fill=1, stroke=0)

        ruta_logo = EscarapelaPDFService._ruta_logo_sena()
        logo_alto = EscarapelaPDFService.BANDA_ALTO - 10 * mm
        if ruta_logo.exists():
            try:
                from PIL import Image
                with Image.open(ruta_logo) as img:
                    w_img, h_img = img.size
                    ratio = logo_alto / h_img
                    logo_ancho = w_img * ratio
                c.drawImage(
                    str(ruta_logo),
                    EscarapelaPDFService.MARGEN,
                    EscarapelaPDFService.PAGE_H - EscarapelaPDFService.BANDA_ALTO + 5 * mm,
                    width=logo_ancho,
                    height=logo_alto,
                    mask='auto',
                )
            except Exception:
                pass

        c.setFillColor(white)
        texto_x = EscarapelaPDFService.MARGEN + 28 * mm
        texto_y = EscarapelaPDFService.PAGE_H - 12 * mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(texto_x, texto_y, 'SENA — FERIA DE PROYECTOS PRODUCTIVOS')

        texto_y2 = EscarapelaPDFService.PAGE_H - 20 * mm
        c.setFont('Helvetica', 10)
        evento_nombre = evento.nombre if evento else 'Evento'
        max_chars = 45
        if len(evento_nombre) > max_chars:
            evento_nombre = evento_nombre[:max_chars - 3] + '...'
        c.drawString(texto_x, texto_y2, evento_nombre)

    @staticmethod
    def _dibujar_rol(c, persona):
        color = COLORES_ROL.get(persona.tipo_persona, COLOR_SENA_VERDE)
        etiqueta = ETIQUETAS_ROL.get(persona.tipo_persona, persona.tipo_persona)

        badge_x = EscarapelaPDFService.MARGEN
        badge_y = EscarapelaPDFService.PAGE_H - EscarapelaPDFService.BANDA_ALTO - 16 * mm
        badge_ancho = 42 * mm
        badge_alto = 10 * mm
        radio = 2 * mm

        c.setFillColor(color)
        c.roundRect(badge_x, badge_y, badge_ancho, badge_alto, radio, fill=1, stroke=0)

        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 10)
        texto_ancho = c.stringWidth(etiqueta, 'Helvetica-Bold', 10)
        c.drawString(
            badge_x + (badge_ancho - texto_ancho) / 2,
            badge_y + 3 * mm,
            etiqueta,
        )

    @staticmethod
    def _dibujar_nombre(c, persona):
        nombre = persona.nombre_completo
        area_x = EscarapelaPDFService.MARGEN
        area_w = EscarapelaPDFService.PAGE_W - 2 * EscarapelaPDFService.MARGEN - EscarapelaPDFService.QR_SIZE - 5 * mm

        y = EscarapelaPDFService.PAGE_H - EscarapelaPDFService.BANDA_ALTO - 32 * mm

        tamano = 16
        fuente = 'Helvetica-Bold'
        while tamano > 10:
            ancho = c.stringWidth(nombre, fuente, tamano)
            if ancho <= area_w:
                break
            tamano -= 1

        c.setFillColor(black)
        c.setFont(fuente, tamano)
        c.drawString(area_x, y, nombre)

    @staticmethod
    def _dibujar_detalles(c, persona):
        info = EscarapelaPDFService._info_persona(persona)
        y = EscarapelaPDFService.PAGE_H - EscarapelaPDFService.BANDA_ALTO - 44 * mm
        x = EscarapelaPDFService.MARGEN

        lineas = []
        if info['institucion']:
            lineas.append(('I.E.: ', info['institucion']))
        if info['programa']:
            lineas.append(('Programa: ', info['programa']))
        if info['proyecto']:
            lineas.append(('Proyecto: ', info['proyecto']))
        if info['extra']:
            lineas.append(('', info['extra']))

        c.setFont('Helvetica', 8)
        c.setFillColor(HexColor('#333333'))

        for etiqueta, valor in lineas:
            if y < 15 * mm:
                break
            texto_completo = f'{etiqueta}{valor}'
            area_w = EscarapelaPDFService.PAGE_W - 2 * EscarapelaPDFService.MARGEN - EscarapelaPDFService.QR_SIZE - 5 * mm
            while c.stringWidth(texto_completo, 'Helvetica', 8) > area_w and len(valor) > 10:
                valor = valor[:-4] + '...'
                texto_completo = f'{etiqueta}{valor}'
            c.drawString(x, y, texto_completo)
            y -= 4.2 * mm

    @staticmethod
    def _dibujar_qr(c, persona):
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        qr_x = EscarapelaPDFService.PAGE_W - EscarapelaPDFService.MARGEN - EscarapelaPDFService.QR_SIZE
        qr_y = EscarapelaPDFService.MARGEN

        try:
            c.drawImage(
                ruta_qr,
                qr_x,
                qr_y,
                width=EscarapelaPDFService.QR_SIZE,
                height=EscarapelaPDFService.QR_SIZE,
                mask='auto',
            )
        except Exception:
            c.setStrokeColor(HexColor('#cccccc'))
            c.setFillColor(HexColor('#f5f5f5'))
            c.rect(qr_x, qr_y, EscarapelaPDFService.QR_SIZE, EscarapelaPDFService.QR_SIZE, fill=1, stroke=1)
            c.setFillColor(HexColor('#999999'))
            c.setFont('Helvetica', 7)
            c.drawCentredString(
                qr_x + EscarapelaPDFService.QR_SIZE / 2,
                qr_y + EscarapelaPDFService.QR_SIZE / 2,
                'QR no disponible',
            )

    @staticmethod
    def _renderizar_hoja(c, persona, evento):
        EscarapelaPDFService._dibujar_encabezado(c, evento)
        EscarapelaPDFService._dibujar_rol(c, persona)
        EscarapelaPDFService._dibujar_nombre(c, persona)
        EscarapelaPDFService._dibujar_detalles(c, persona)
        EscarapelaPDFService._dibujar_qr(c, persona)
        c.showPage()

    @staticmethod
    def generar_individual(persona, evento):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A6))
        EscarapelaPDFService._renderizar_hoja(c, persona, evento)
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generar_lote(qs_personas, evento, titulo_lote=None):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A6))
        for persona in qs_personas:
            EscarapelaPDFService._renderizar_hoja(c, persona, evento)
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
