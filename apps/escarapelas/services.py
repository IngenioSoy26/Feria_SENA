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

# =================================================================
# COORDENADAS AJUSTADAS A LA NUEVA Credencial.png (1024 x 1536 px → 107x135 mm)
# Foto de referencia: Jorge Arrieta (enviada x usuario)
# 0,0 = esquina inf-izq (ReportLab)
# ESTRATEGIA: NO REDIBUJAR NINGÚN MARCO; los marcos YA ESTÁN DIBUJADOS en la PNG.
# Solo: (1) capa blanca opaca TAPA el badge verde original + badge nuevo color.
#       (2) TEXTOS y QR SOBRE LAS CAJAS EXISTENTES sin contornos nuevos.
# =================================================================

POS_BADGE = {
    'x':   13.4 * mm,
    'y':   82.0 * mm,
    'w':   80.2 * mm,
    'h':   15.0 * mm,
    'r':    7.0 * mm,
    'dy_txt': 4.2 * mm,
    'size':   19,
}

# ---------------------------------------------------------------------------
# CAJA NOMBRE BLANCA con BORDE color rol → FONDO BLANCO SÓLIDO + TEXTO dentro.
#   - Oculta exactamente el contenido donde irán Nombre/IE/Municipio.
#   - NUNCA sobrepasa: Y_top = badge.y - 3mm espacio visual
#   - NUNCA llega al desierto inferior.
# ---------------------------------------------------------------------------
POS_CAJA_NOMBRE = {
    'x':      8 * mm,
    'y':     42 * mm,
    'w':     91 * mm,
    'h':     37 * mm,
    'r':    8.5 * mm,
    'borde_grosor': 2.2,
    'padding_lados':  5 * mm,
    'y1_texto': 72.5 * mm,   # Nombre (arriba)
    'y2_texto': 64.5 * mm,   # I.E.
    'y3_texto': 56.5 * mm,   # Municipio
    'size_1': 20,
    'size_2': 11,
    'size_3': 10.5,
}

# ---------------------------------------------------------------------------
# CAJA DOCUMENTO BLANCA borde color rol → FONDO BLANCO SÓLIDO
#   - No toca el mar ni el verde del badge, solo zona central limpia.
# ---------------------------------------------------------------------------
POS_CAJA_DOC = {
    'x':  23 * mm,
    'y':  30 * mm,
    'w':  61 * mm,
    'h':  10 * mm,
    'r':   6 * mm,
    'borde_grosor': 2.0,
    'y_texto': 33.0 * mm,
    'size':   14,
}

# ---------------------------------------------------------------------------
# CAJA INFERIOR GRANDE (Proyecto + QR) borde color rol.
#   - DENTRO del hueco "foto" de la plantilla → NUNCA sobre el desierto/mar.
#   - Borde GROSOR color rol → igual que el ejemplo Jorge.
# ---------------------------------------------------------------------------
POS_CAJA_INFERIOR = {
    'x':  19 * mm,
    'y':   5 * mm,
    'w':  69 * mm,
    'h':  23 * mm,      # temporalmente se sobreescribe abajo
    'r':  9.5 * mm,
    'borde_grosor_exterior': 3.2,
    'borde_grosor_interior': 1.2,
    'padding':      4 * mm,
    'y_proyecto':  24.5 * mm,
    'size_label':  11.5,
    'size_valor':  12.5,
    'qr_size':     0,       # se calcula después
    'qr_centro_x': 53.5 * mm,
    'qr_y_inf':    8.5 * mm,
}

# Ampliar la caja inferior a 44mm de alto (para QR 36mm + texto proyecto arriba)
POS_CAJA_INFERIOR['h'] = 44 * mm
POS_CAJA_INFERIOR['qr_size'] = 36 * mm
POS_CAJA_INFERIOR['y_proyecto'] = POS_CAJA_INFERIOR['y'] + POS_CAJA_INFERIOR['h'] - 10 * mm  # 10mm debajo del techo
POS_CAJA_INFERIOR['qr_centro_x'] = (POS_CAJA_INFERIOR['x'] + POS_CAJA_INFERIOR['x'] + POS_CAJA_INFERIOR['w']) / 2
POS_CAJA_INFERIOR['qr_y_inf']  = POS_CAJA_INFERIOR['y'] + 4 * mm


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
        x = dx + POS_BADGE['x']
        y = dy + POS_BADGE['y']
        w = POS_BADGE['w']
        h = POS_BADGE['h']
        c.setFillColor(white)
        c.roundRect(x - 0.4 * mm, y - 0.4 * mm,
                    w + 0.8 * mm, h + 0.8 * mm,
                    POS_BADGE['r'], fill=1, stroke=0)
        c.setFillColor(color_f)
        c.roundRect(x, y, w, h, POS_BADGE['r'], fill=1, stroke=0)
        EscarapelaPDFService._centrar(
            c, texto,
            dy + POS_BADGE['y'] + POS_BADGE['dy_txt'],
            'Helvetica-Bold', POS_BADGE['size'], color_t, w - 6 * mm, dx,
        )

    @staticmethod
    def _color_borde_rol(rol):
        if rol == 'APRENDIZ':    return COLOR_APRENDIZ
        if rol == 'INSTRUCTOR':  return COLOR_INSTRUCTOR
        if rol == 'INVITADO':    return COLOR_INVITADO
        if rol == 'ORGANIZADOR': return COLOR_ORGANIZADOR
        return COLOR_APRENDIZ

    @staticmethod
    def _caja_nombre_contenido(c, persona, info, rol, dx=0, dy=0):
        p = POS_CAJA_NOMBRE
        x, y, w, h = dx + p['x'], dy + p['y'], p['w'], p['h']
        borde = EscarapelaPDFService._color_borde_rol(rol)
        c.setFillColor(white)
        c.roundRect(x, y, w, h, p['r'], fill=1, stroke=0)
        c.setStrokeColor(borde)
        c.setLineWidth(p['borde_grosor'])
        c.roundRect(x, y, w, h, p['r'], fill=0, stroke=1)
        # Texto interno
        nombre_txt = (persona.nombre_completo or '').upper()
        max_w = w - 2 * p['padding_lados']
        EscarapelaPDFService._centrar(
            c, nombre_txt, dy + p['y1_texto'],
            'Helvetica-Bold', p['size_1'], black, max_w, dx,
        )
        line2 = ''
        if info['institucion']:
            line2 = 'I.E. ' + (info['institucion'] or '')
        elif info['programa']:
            line2 = info['programa']
        elif info['extra']:
            line2 = info['extra']
        if line2:
            EscarapelaPDFService._centrar(
                c, line2, dy + p['y2_texto'],
                'Helvetica', p['size_2'], GRIS_OSCURO, max_w, dx,
            )
        line3 = ''
        if info['municipio_ie']:
            line3 = info['municipio_ie'].upper() + ' - LA GUAJIRA'
        elif info['codigo_ficha']:
            line3 = 'FICHA ' + str(info['codigo_ficha'])
        if line3:
            EscarapelaPDFService._centrar(
                c, line3, dy + p['y3_texto'],
                'Helvetica', p['size_3'], GRIS_MEDIO, max_w, dx,
            )

    @staticmethod
    def _caja_documento_contenido(c, info, rol, dx=0, dy=0):
        p = POS_CAJA_DOC
        x, y, w, h = dx + p['x'], dy + p['y'], p['w'], p['h']
        borde = EscarapelaPDFService._color_borde_rol(rol)
        c.setFillColor(white)
        c.roundRect(x, y, w, h, p['r'], fill=1, stroke=0)
        c.setStrokeColor(borde)
        c.setLineWidth(p['borde_grosor'])
        c.roundRect(x, y, w, h, p['r'], fill=0, stroke=1)
        tipo = (info['tipo_identificacion'] or 'CC')
        num = info['numero_identificacion'] or ''
        label = f'{tipo}:'
        val = f' {num}'
        tam = p['size']
        ancho_l = c.stringWidth(label, 'Helvetica-Bold', tam)
        max_w_v = w - ancho_l - 8 * mm
        ancho_v = c.stringWidth(val, 'Helvetica-Bold', tam)
        while ancho_v > max_w_v and tam > 6:
            tam -= 0.5
            ancho_l = c.stringWidth(label, 'Helvetica-Bold', tam)
            max_w_v = w - ancho_l - 8 * mm
            ancho_v = c.stringWidth(val, 'Helvetica-Bold', tam)
        ancho_total = ancho_l + ancho_v
        x1 = dx + (EscarapelaPDFService.W - ancho_total) / 2
        x2 = x1 + ancho_l
        c.setFillColor(COLOR_SENA_VERDE_OSCURO)
        c.setFont('Helvetica-Bold', tam)
        c.drawString(x1, dy + p['y_texto'], label)
        c.setFillColor(black)
        c.drawString(x2, dy + p['y_texto'], val)

    @staticmethod
    def _caja_inferior_proyecto_y_qr(c, persona, info, rol, dx=0, dy=0):
        """CAJA BLANCA con BORDE color rol GROSOR (doble borde exterior+interior):
               ______________    ← exterior color rol
              |  _________  |    ← interior blanco con línea color rol 1mm
              | |Proyecto: |  |    10mm desde el techo
              | |          |  |
              | |   QR 36mm|  |    4mm desde el suelo
              | |          |  |
              | |__________|  |
              |______________|
        """
        p = POS_CAJA_INFERIOR
        x, y, w, h = dx + p['x'], dy + p['y'], p['w'], p['h']
        borde = EscarapelaPDFService._color_borde_rol(rol)
        # --- exterior (color rol, GROSOR) ---
        c.setFillColor(borde)
        c.roundRect(x, y, w, h, p['r'], fill=1, stroke=0)
        # --- interior blanco + línea borde color rol delgada ---
        pad = p['padding']
        xi, yi, wi, hi = x + pad, y + pad, w - 2 * pad, h - 2 * pad
        c.setFillColor(white)
        c.roundRect(xi, yi, wi, hi, max(p['r'] - 4 * mm, 1 * mm), fill=1, stroke=0)
        c.setStrokeColor(borde)
        c.setLineWidth(p['borde_grosor_interior'])
        c.roundRect(xi, yi, wi, hi, max(p['r'] - 4 * mm, 1 * mm), fill=0, stroke=1)
        # --- TEXTO PROYECTO (10mm debajo techo interior) ---
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
        elif info['institucion']:
            valor = info['institucion']
        else:
            valor = ''
        if valor:
            label = 'Proyecto: '
            tam_l = p['size_label']
            tam_v = p['size_valor']
            max_w_total = wi - 4 * mm
            ancho_l = c.stringWidth(label, 'Helvetica-Bold', tam_l)
            ancho_v = c.stringWidth(valor, 'Helvetica-Bold', tam_v)
            while ancho_v > max_w_total - ancho_l and tam_v > 7:
                tam_v -= 0.5
                ancho_v = c.stringWidth(valor, 'Helvetica-Bold', tam_v)
            ancho_total = ancho_l + ancho_v
            x1 = xi + (wi - ancho_total) / 2
            x2 = x1 + ancho_l
            yt = dy + p['y_proyecto']
            c.setFillColor(black)
            c.setFont('Helvetica-Bold', tam_l)
            c.drawString(x1, yt, label)
            c.setFont('Helvetica-Bold', tam_v)
            c.drawString(x2, yt, valor)
        # --- QR (4mm desde el suelo interior) ---
        qr_s = p['qr_size']
        qr_x = dx + p['qr_centro_x'] - qr_s / 2
        qr_y = dy + p['qr_y_inf']
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        try:
            c.drawImage(ruta_qr, qr_x, qr_y, width=qr_s, height=qr_s, mask='auto')
        except Exception:
            pass

    @staticmethod
    def _dibujar_frente(c, persona, evento, dx=0, dy=0):
        info = EscarapelaPDFService._info_persona(persona)
        rol = persona.tipo_persona
        # Orden de capas (inferior → superior):
        EscarapelaPDFService._dibujar_imagen_fondo(c, dx, dy)
        EscarapelaPDFService._badge_rol(c, rol, dx, dy)
        EscarapelaPDFService._caja_nombre_contenido(c, persona, info, rol, dx, dy)
        EscarapelaPDFService._caja_documento_contenido(c, info, rol, dx, dy)
        EscarapelaPDFService._caja_inferior_proyecto_y_qr(c, persona, info, rol, dx, dy)

    @staticmethod
    def _renderizar_persona(c, persona, evento, dx=0, dy=0):
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
