import io
from pathlib import Path

from django.conf import settings

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black

from apps.personas.services import QrService


ESCARAPELA_W = 107 * mm
ESCARAPELA_H = 135 * mm
CARTA_W, CARTA_H = letter
GUTTER = 1.5 * mm

COLOR_APRENDIZ    = HexColor('#39A900')
COLOR_INSTRUCTOR  = HexColor('#7B1FA2')
COLOR_INVITADO    = HexColor('#FBC02D')
COLOR_ORGANIZADOR = HexColor('#455A64')

COLOR_SENA_VERDE_OSCURO = HexColor('#1F6B00')
GRIS_OSCURO = HexColor('#222222')
GRIS_MEDIO  = HexColor('#444444')

BADGE_ROL = {
    'APRENDIZ':     (COLOR_APRENDIZ,   white),
    'INSTRUCTOR':   (COLOR_INSTRUCTOR, white),
    'INVITADO':     (COLOR_INVITADO,   black),
    'ORGANIZADOR':  (COLOR_ORGANIZADOR, white),
}
BADGE_ROL_TEXTO = {
    'APRENDIZ':     'APRENDIZ',
    'INSTRUCTOR':   'INSTRUCTOR',
    'INVITADO':     'INVITADO',
    'ORGANIZADOR':  'ORGANIZADOR',
}
BADGE_ROL_BORDE = {
    'APRENDIZ':     COLOR_APRENDIZ,
    'INSTRUCTOR':   COLOR_INSTRUCTOR,
    'INVITADO':     COLOR_INVITADO,
    'ORGANIZADOR':  COLOR_ORGANIZADOR,
}

# =================================================================
# COORDENADAS FIJAS sobre 107x135mm (0,0 = inf-izq)
# AJUSTADAS al modelo JORGE ARRIETA (1 sola cara):
#   ARRIBA → ABAJO:
#   [BADGE ROL]
#   [CAJA NOMBRE 3 LÍNEAS (Nombre / I.E. / Municipio)]
#   [CAJA DOCUMENTO  (CC: xxx)]
#   [TEXTO PROYECTO]
#   [CAJA QR GRANDE abajo con borde color rol]
# =================================================================

POS_BADGE_ROL = {
    'x': 16 * mm,  'y': 83 * mm,
    'w': 75 * mm,  'h': 13 * mm,
    'r': 7 * mm,
    'dy_txt': 4.2 * mm,
    'size':   18,
}

POS_CAJA_NOMBRE = {
    'x':  9 * mm,  'y': 49 * mm,
    'w': 89 * mm,  'h': 32 * mm,
    'r': 9 * mm,
    'borde_grosor': 2.4,
    'size_1': 19,    # Nombre grande
    'size_2': 10.5,  # I.E. mediana
    'size_3': 10,    # Municipio chica
}

POS_CAJA_DOC = {
    'x': 30 * mm,  'y': 38 * mm,
    'w': 47 * mm,  'h': 10 * mm,
    'r': 6 * mm,
    'borde_grosor': 2.2,
    'dy_txt': 2.8 * mm,
    'size':   13,
}

POS_PROYECTO = {
    'y': 30 * mm,
    'size_label': 11.5,
    'size_valor': 12,
}

POS_CAJA_QR = {
    'x': 22 * mm,  'y': 8 * mm,
    'w': 63 * mm,  'h': 21 * mm,  # alto crece hacia arriba desde y
    'r': 9 * mm,
    'borde_grosor': 3,
    'qr_size':     20 * mm,  # NO USE; calculamos a continuación
}
# Ajustamos el alto de la caja QR para que quepa un QR cuadrado 44x44mm
POS_CAJA_QR['h'] = 46 * mm
POS_CAJA_QR['qr_size_inner'] = 38 * mm


class EscarapelaPDFService:
    W, H = ESCARAPELA_W, ESCARAPELA_H

    @staticmethod
    def _ruta_credencial():
        static_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / 'static']
        return Path(static_dirs[0]) / 'img' / 'Credencial.png'

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
            'codigo_proyecto': None,
            'municipio_ie': None,
            'rol_display': None,
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
                info['codigo_proyecto'] = getattr(perfil.proyecto, 'codigo', None)
                if perfil.proyecto.institucion:
                    ie = perfil.proyecto.institucion
                    info['institucion'] = ie.nombre
                    try:
                        info['municipio_ie'] = ie.municipio.nombre if ie.municipio else None
                    except Exception:
                        info['municipio_ie'] = None
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
    def _centrar(c, texto, y, fuente, tam, color, max_w, dx):
        if max_w < 1:
            return
        ancho = c.stringWidth(texto, fuente, tam)
        while ancho > max_w and tam > 6:
            tam -= 0.5
            ancho = c.stringWidth(texto, fuente, tam)
        c.setFillColor(color)
        c.setFont(fuente, tam)
        x = dx + (EscarapelaPDFService.W - ancho) / 2
        c.drawString(x, y, texto)

    @staticmethod
    def _izq(c, texto, x_mm, y, fuente, tam, color, dx=0):
        c.setFillColor(color)
        c.setFont(fuente, tam)
        c.drawString(dx + x_mm, y, texto)

    @staticmethod
    def _dibujar_imagen_fondo(c, dx=0, dy=0):
        ruta = EscarapelaPDFService._ruta_credencial()
        if not ruta.exists():
            c.setFillColor(HexColor('#FFF8E7'))
            c.rect(dx, dy, EscarapelaPDFService.W, EscarapelaPDFService.H, fill=1, stroke=0)
            return
        try:
            c.drawImage(
                str(ruta),
                dx,
                dy,
                width=EscarapelaPDFService.W,
                height=EscarapelaPDFService.H,
                mask='auto',
                preserveAspectRatio=False,
            )
        except Exception:
            pass

    @staticmethod
    def _badge_rol(c, rol, dx=0, dy=0):
        color_f, color_t = BADGE_ROL.get(rol, BADGE_ROL['APRENDIZ'])
        texto = BADGE_ROL_TEXTO.get(rol, rol or '')
        x = dx + POS_BADGE_ROL['x']
        y = dy + POS_BADGE_ROL['y']
        w = POS_BADGE_ROL['w']
        h = POS_BADGE_ROL['h']
        # Tapa el badge verde original de la plantilla (blanco 1mm extra alrededor)
        c.setFillColor(white)
        c.roundRect(x - 0.5 * mm, y - 0.5 * mm,
                    w + 1 * mm, h + 1 * mm,
                    POS_BADGE_ROL['r'], fill=1, stroke=0)
        # Pintar badge color
        c.setFillColor(color_f)
        c.roundRect(x, y, w, h, POS_BADGE_ROL['r'], fill=1, stroke=0)
        # Borde sutil
        c.setStrokeColor(HexColor('#000000'))
        c.setStrokeAlpha(0.12)
        c.setLineWidth(0.5)
        c.roundRect(x, y, w, h, POS_BADGE_ROL['r'], fill=0, stroke=1)
        c.setStrokeAlpha(1)
        EscarapelaPDFService._centrar(
            c, texto,
            dy + POS_BADGE_ROL['y'] + POS_BADGE_ROL['dy_txt'],
            'Helvetica-Bold', POS_BADGE_ROL['size'], color_t, w - 6 * mm, dx,
        )

    @staticmethod
    def _caja_nombre_3lineas(c, persona, info, dx=0, dy=0):
        p = POS_CAJA_NOMBRE
        x = dx + p['x']
        y = dy + p['y']
        w = p['w']
        h = p['h']
        borde = BADGE_ROL_BORDE.get(persona.tipo_persona, COLOR_APRENDIZ)
        # Tapa el contenido original de la plantilla en esa zona
        c.setFillColor(white)
        c.roundRect(x, y, w, h, p['r'], fill=1, stroke=0)
        # Borde color rol
        c.setStrokeColor(borde)
        c.setLineWidth(p['borde_grosor'])
        c.roundRect(x, y, w, h, p['r'], fill=0, stroke=1)
        # ===== LÍNEA 1: NOMBRE COMPLETO (grande) =====
        nombre_txt = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar(
            c, nombre_txt,
            dy + p['y'] + h - 12 * mm,
            'Helvetica-Bold', p['size_1'], black, w - 8 * mm, dx
        )
        # ===== LÍNEA 2: I.E. NOMBRE (mediana) =====
        line2 = ''
        if info['institucion']:
            line2 = 'I.E. ' + (info['institucion'] or '')
        elif info['programa']:
            line2 = info['programa']
        elif info['extra']:
            line2 = info['extra']
        if line2:
            EscarapelaPDFService._centrar(
                c, line2,
                dy + p['y'] + h - 20 * mm,
                'Helvetica', p['size_2'], GRIS_OSCURO, w - 10 * mm, dx
            )
        # ===== LÍNEA 3: MUNICIPIO - LA GUAJIRA (chica) =====
        line3 = ''
        if info['municipio_ie']:
            line3 = info['municipio_ie'].upper() + ' - LA GUAJIRA'
        elif info['codigo_ficha']:
            line3 = 'FICHA ' + str(info['codigo_ficha'])
        if line3:
            EscarapelaPDFService._centrar(
                c, line3,
                dy + p['y'] + h - 27 * mm,
                'Helvetica', p['size_3'], GRIS_MEDIO, w - 10 * mm, dx
            )

    @staticmethod
    def _caja_documento(c, info, rol, dx=0, dy=0):
        p = POS_CAJA_DOC
        x = dx + p['x']
        y = dy + p['y']
        w = p['w']
        h = p['h']
        borde = BADGE_ROL_BORDE.get(rol, COLOR_APRENDIZ)
        # Tapa el contenido original
        c.setFillColor(white)
        c.roundRect(x, y, w, h, p['r'], fill=1, stroke=0)
        c.setStrokeColor(borde)
        c.setLineWidth(p['borde_grosor'])
        c.roundRect(x, y, w, h, p['r'], fill=0, stroke=1)
        # Contenido: "CC: 1234567892"
        tipo = (info['tipo_identificacion'] or 'CC')
        num = info['numero_identificacion'] or ''
        txt1 = f'{tipo}:'
        txt2 = f' {num}'
        # Medir y centrar como bloque compuesto
        tam = p['size']
        ancho1 = c.stringWidth(txt1, 'Helvetica-Bold', tam)
        max_w_num = w - ancho1 - 8 * mm
        ancho2 = c.stringWidth(txt2, 'Helvetica-Bold', tam)
        while ancho2 > max_w_num and tam > 6:
            tam -= 0.5
            ancho1 = c.stringWidth(txt1, 'Helvetica-Bold', tam)
            max_w_num = w - ancho1 - 8 * mm
            ancho2 = c.stringWidth(txt2, 'Helvetica-Bold', tam)
        ancho_total = ancho1 + ancho2
        x1 = dx + (EscarapelaPDFService.W - ancho_total) / 2
        x2 = x1 + ancho1
        yt = dy + p['y'] + p['dy_txt']
        c.setFillColor(COLOR_SENA_VERDE_OSCURO)
        c.setFont('Helvetica-Bold', tam)
        c.drawString(x1, yt, txt1)
        c.setFillColor(black)
        c.drawString(x2, yt, txt2)

    @staticmethod
    def _texto_proyecto(c, info, dx=0, dy=0):
        p = POS_PROYECTO
        if not (info['proyecto'] or info['programa'] or info['extra'] or info['codigo_proyecto']):
            return
        if info['codigo_proyecto'] and info['proyecto']:
            valor = info['codigo_proyecto'] + ' - ' + info['proyecto']
        elif info['proyecto']:
            valor = info['proyecto']
        elif info['codigo_ficha'] and info['programa']:
            valor = info['programa'] + ' · FICHA ' + str(info['codigo_ficha'])
        elif info['programa']:
            valor = info['programa']
        elif info['extra']:
            valor = info['extra']
        else:
            valor = ''
        if not valor:
            return
        label = 'Proyecto: '
        tam_l = p['size_label']
        tam_v = p['size_valor']
        max_w = EscarapelaPDFService.W - 14 * mm
        ancho_l = c.stringWidth(label, 'Helvetica-Bold', tam_l)
        ancho_v = c.stringWidth(valor, 'Helvetica-Bold', tam_v)
        while ancho_v > max_w - ancho_l and tam_v > 7:
            tam_v -= 0.5
            ancho_v = c.stringWidth(valor, 'Helvetica-Bold', tam_v)
        ancho_total = ancho_l + ancho_v
        x1 = dx + (EscarapelaPDFService.W - ancho_total) / 2
        x2 = x1 + ancho_l
        yt = dy + p['y']
        c.setFillColor(black)
        c.setFont('Helvetica-Bold', tam_l)
        c.drawString(x1, yt, label)
        c.setFillColor(black)
        c.setFont('Helvetica-Bold', tam_v)
        c.drawString(x2, yt, valor)

    @staticmethod
    def _caja_qr(c, persona, rol, dx=0, dy=0):
        p = POS_CAJA_QR
        x = dx + p['x']
        y = dy + p['y']
        w = p['w']
        h = p['h']
        borde = BADGE_ROL_BORDE.get(rol, COLOR_APRENDIZ)
        # Doble borde: exterior color rol (grueso), interior blanco grueso
        # Exterior
        c.setFillColor(borde)
        c.roundRect(x, y, w, h, p['r'], fill=1, stroke=0)
        # Interior blanco
        in_w = w - 6 * mm
        in_h = h - 6 * mm
        in_x = x + 3 * mm
        in_y = y + 3 * mm
        c.setFillColor(white)
        c.roundRect(in_x, in_y, in_w, in_h, p['r'] - 3 * mm, fill=1, stroke=0)
        # QR centrado dentro del blanco interior
        qr_s = min(in_w, in_h) * 0.92
        qr_x = in_x + (in_w - qr_s) / 2
        qr_y = in_y + (in_h - qr_s) / 2
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        try:
            c.drawImage(ruta_qr, qr_x, qr_y, width=qr_s, height=qr_s, mask='auto')
        except Exception:
            pass

    @staticmethod
    def _dibujar_frente(c, persona, evento, dx=0, dy=0):
        info = EscarapelaPDFService._info_persona(persona)
        EscarapelaPDFService._dibujar_imagen_fondo(c, dx, dy)
        EscarapelaPDFService._badge_rol(c, persona.tipo_persona, dx, dy)
        EscarapelaPDFService._caja_nombre_3lineas(c, persona, info, dx, dy)
        EscarapelaPDFService._caja_documento(c, info, persona.tipo_persona, dx, dy)
        EscarapelaPDFService._texto_proyecto(c, info, dx, dy)
        EscarapelaPDFService._caja_qr(c, persona, persona.tipo_persona, dx, dy)

    @staticmethod
    def _renderizar_persona(c, persona, evento, dx=0, dy=0):
        """1 SOLA PÁGINA (1 cara) por persona"""
        EscarapelaPDFService._dibujar_frente(c, persona, evento, dx, dy)
        c.showPage()

    @staticmethod
    def generar_individual(persona, evento):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(EscarapelaPDFService.W, EscarapelaPDFService.H))
        EscarapelaPDFService._renderizar_persona(c, persona, evento)
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def _slots_carta():
        s = []
        for fila in (1, 0):
            for col in (0, 1):
                dx = (CARTA_W - 2 * EscarapelaPDFService.W - GUTTER) / 2 + col * (EscarapelaPDFService.W + GUTTER)
                dy = (CARTA_H - 2 * EscarapelaPDFService.H - GUTTER) / 2 + fila * (EscarapelaPDFService.H + GUTTER)
                s.append((dx, dy))
        return s

    @staticmethod
    def _bloques_carta(c, personas, evento, fn):
        slots = EscarapelaPDFService._slots_carta()
        for i in range(0, len(personas), 4):
            g = personas[i:i + 4]
            for idx, p in enumerate(g):
                dx, dy = slots[idx]
                c.saveState()
                fn(c, p, evento, dx, dy)
                c.restoreState()
            c.showPage()

    @staticmethod
    def generar_lote(qs_personas, evento, titulo_lote=None, formato='CARTA_4X'):
        personas = list(qs_personas)
        buffer = io.BytesIO()
        if formato == 'INDIVIDUAL':
            c = canvas.Canvas(buffer, pagesize=(EscarapelaPDFService.W, EscarapelaPDFService.H))
            for p in personas:
                EscarapelaPDFService._renderizar_persona(c, p, evento)
        else:
            c = canvas.Canvas(buffer, pagesize=letter)
            # SOLO 1 BLOQUE: FRENTES (ya que es 1 sola cara)
            EscarapelaPDFService._bloques_carta(c, personas, evento, EscarapelaPDFService._dibujar_frente)
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generar_por_proyecto(proyecto, formato='CARTA_4X'):
        from apps.personas.models import Persona
        evento = proyecto.evento
        qs = Persona.objects.filter(perfil_aprendiz__proyecto=proyecto, activo=True
                                     ).order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'Proyecto {proyecto.codigo}', formato=formato)

    @staticmethod
    def generar_por_institucion(ie, evento, formato='CARTA_4X'):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto
        ids = list(Proyecto.objects.filter(institucion=ie, evento=evento).values_list('id', flat=True))
        qs = Persona.objects.filter(perfil_aprendiz__proyecto_id__in=ids, activo=True
                                     ).order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'IE {ie.codigo}', formato=formato)

    @staticmethod
    def generar_por_programa(programa, evento, formato='CARTA_4X'):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto
        ids = list(Proyecto.objects.filter(programa=programa, evento=evento).values_list('id', flat=True))
        q1 = Persona.objects.filter(perfil_aprendiz__proyecto_id__in=ids, activo=True)
        q2 = Persona.objects.filter(perfil_instructor__programas=programa, activo=True)
        qs = (q1 | q2).distinct().order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'PR {programa.codigo}', formato=formato)

    @staticmethod
    def generar_completo(evento, formato='CARTA_4X'):
        from django.db.models import Q
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto
        proy = list(Proyecto.objects.filter(evento=evento).values_list('id', flat=True))
        ins = list(Proyecto.objects.filter(evento=evento
                    ).exclude(instructor_responsable__isnull=True
                    ).values_list('instructor_responsable__persona_id', flat=True))
        qs = Persona.objects.filter(activo=True).filter(
            Q(perfil_aprendiz__proyecto_id__in=proy)
            | Q(id__in=ins)
            | Q(tipo_persona__in=['INVITADO', 'ORGANIZADOR'])
        ).distinct().order_by('tipo_persona', 'apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, 'Completo', formato=formato)
