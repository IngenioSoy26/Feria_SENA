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
# COORDENADAS SOBRE DISEÑO REAL DE Credencial.png (971×1619 px → 107×135 mm).
# 0,0 = esquina inf-izq (ReportLab).
# AJUSTADAS para NO REDIBUJAR MARCOS (la plantilla YA LOS TIENE):
#   - SOLO TAPAMOS el badge verde fijo con blanco opaco + pintamos nuevo badge.
#   - El resto: SOLO TEXTO sobre las CAJAS QUE YA EXISTEN en la PNG.
# =================================================================

POS_BADGE = {
    'x':      14 * mm,     # aprox 13.88 medido
    'y':      78 * mm,     # BADGE ORIGINAL tapado ~ 67.5 .. 82.5 H=15 → y inf = 67.5
    'w':      79 * mm,
    'h':      15 * mm,
    'r':      7 * mm,
    'dy_txt': 4.2 * mm,
    'size':   18,
}

POS_TEXTO_NOMBRE = {
    # Alineado sobre la CAJA BLANCA SUPERIOR de Credencial.png (nombre/IE/municipio)
    'w':      88 * mm,
    'y1': 57.5 * mm,  # Nombre (línea 1)
    'y2': 50.5 * mm,  # IE (línea 2)
    'y3': 44.5 * mm,  # Municipio (línea 3)
    'size_1': 19,
    'size_2': 10.5,
    'size_3': 10,
}

POS_TEXTO_DOC = {
    # Sobre la CAJA VERDE DOCUMENTO "CC: xxxxx" de la plantilla
    'w':      55 * mm,
    'y': 32 * mm,
    'size':   13,
}

POS_TEXTO_PROYECTO = {
    # Dentro de la CAJA GRANDE INFERIOR (arriba del QR). Texto sin marco nuevo.
    'w': 60 * mm,
    'y': 26 * mm,
    'size_label': 11,
    'size_valor': 12,
}

POS_QR = {
    # Dentro de la CAJA GRANDE INFERIOR (no sobre el mar).
    'size': 22 * mm,
    'centro_x': 53.5 * mm,  # ~ centro 107/2
    'y_inf':    4.5 * mm,   # desde esquina inf
}


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
        """SÓLO redibuja la zona del badge (capa blanca opaca + nuevo badge color rol)."""
        color_f, color_t = BADGE_ROL.get(rol, BADGE_ROL['APRENDIZ'])
        texto = BADGE_ROL_TEXTO.get(rol, rol or '')
        x = dx + POS_BADGE['x']
        y = dy + POS_BADGE['y']
        w = POS_BADGE['w']
        h = POS_BADGE['h']
        # Capa BLANCA opaca: TAPA el badge verde "APRENDIZ" de la plantilla.
        c.setFillColor(white)
        c.roundRect(x - 0.4 * mm, y - 0.4 * mm,
                    w + 0.8 * mm, h + 0.8 * mm,
                    POS_BADGE['r'], fill=1, stroke=0)
        # Badge color nuevo
        c.setFillColor(color_f)
        c.roundRect(x, y, w, h, POS_BADGE['r'], fill=1, stroke=0)
        EscarapelaPDFService._centrar(
            c, texto,
            dy + POS_BADGE['y'] + POS_BADGE['dy_txt'],
            'Helvetica-Bold', POS_BADGE['size'], color_t, w - 6 * mm, dx,
        )

    @staticmethod
    def _escribir_nombre_3lineas(c, persona, info, dx=0, dy=0):
        """SOLO TEXTO (sin caja): Escribe sobre la CAJA NOMBRE ya dibujada en Credencial.png."""
        p = POS_TEXTO_NOMBRE
        # Línea 1: Nombre
        nombre_txt = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar(
            c, nombre_txt, dy + p['y1'],
            'Helvetica-Bold', p['size_1'], black, p['w'], dx,
        )
        # Línea 2: I.E. NOMBRE
        line2 = ''
        if info['institucion']:
            line2 = 'I.E. ' + (info['institucion'] or '')
        elif info['programa']:
            line2 = info['programa']
        elif info['extra']:
            line2 = info['extra']
        if line2:
            EscarapelaPDFService._centrar(
                c, line2, dy + p['y2'],
                'Helvetica', p['size_2'], GRIS_OSCURO, p['w'] - 4 * mm, dx
            )
        # Línea 3: MUNICIPIO - LA GUAJIRA
        line3 = ''
        if info['municipio_ie']:
            line3 = info['municipio_ie'].upper() + ' - LA GUAJIRA'
        elif info['codigo_ficha']:
            line3 = 'FICHA ' + str(info['codigo_ficha'])
        if line3:
            EscarapelaPDFService._centrar(
                c, line3, dy + p['y3'],
                'Helvetica', p['size_3'], GRIS_MEDIO, p['w'] - 4 * mm, dx
            )

    @staticmethod
    def _escribir_documento(c, info, dx=0, dy=0):
        """SOLO TEXTO: sobre la CAJA DOCUMENTO verde de Credencial.png."""
        p = POS_TEXTO_DOC
        tipo = (info['tipo_identificacion'] or 'CC')
        num = info['numero_identificacion'] or ''
        label = f'{tipo}:'
        val = f' {num}'
        tam = p['size']
        ancho_l = c.stringWidth(label, 'Helvetica-Bold', tam)
        max_w_v = p['w'] - ancho_l - 6 * mm
        ancho_v = c.stringWidth(val, 'Helvetica-Bold', tam)
        while ancho_v > max_w_v and tam > 6:
            tam -= 0.5
            ancho_l = c.stringWidth(label, 'Helvetica-Bold', tam)
            max_w_v = p['w'] - ancho_l - 6 * mm
            ancho_v = c.stringWidth(val, 'Helvetica-Bold', tam)
        ancho_total = ancho_l + ancho_v
        x1 = dx + (EscarapelaPDFService.W - ancho_total) / 2
        x2 = x1 + ancho_l
        yt = dy + p['y']
        c.setFillColor(COLOR_SENA_VERDE_OSCURO)
        c.setFont('Helvetica-Bold', tam)
        c.drawString(x1, yt, label)
        c.setFillColor(black)
        c.drawString(x2, yt, val)

    @staticmethod
    def _escribir_proyecto_y_qr(c, persona, info, rol, dx=0, dy=0):
        """DENTRO de la CAJA GRANDE INFERIOR de la plantilla:
             → Arriba: "Proyecto: COD - Nombre"
             → Abajo: QR centrado (sin borde nuevo)
           NO DIBUJA CAJAS NUEVAS (la plantilla tiene la caja).
        """
        # --- TEXTO PROYECTO ---
        p = POS_TEXTO_PROYECTO
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
            max_w = p['w']
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
            c.setFont('Helvetica-Bold', tam_v)
            c.drawString(x2, yt, valor)
        # --- QR ---
        q = POS_QR
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        try:
            qr_x = dx + q['centro_x'] - q['size'] / 2
            qr_y = dy + q['y_inf']
            c.drawImage(ruta_qr, qr_x, qr_y, width=q['size'], height=q['size'], mask='auto')
        except Exception:
            pass

    @staticmethod
    def _dibujar_frente(c, persona, evento, dx=0, dy=0):
        info = EscarapelaPDFService._info_persona(persona)
        # Orden de capas:
        EscarapelaPDFService._dibujar_imagen_fondo(c, dx, dy)                # 1) Fondo = TU plantilla
        EscarapelaPDFService._badge_rol(c, persona.tipo_persona, dx, dy)     # 2) Tapa + badge color rol
        EscarapelaPDFService._escribir_nombre_3lineas(c, persona, info, dx, dy)  # 3) Nombre 3 líneas
        EscarapelaPDFService._escribir_documento(c, info, dx, dy)            # 4) CC: xxxx
        EscarapelaPDFService._escribir_proyecto_y_qr(c, persona, info, persona.tipo_persona, dx, dy)  # 5) Proyecto + QR dentro de la caja grande

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
