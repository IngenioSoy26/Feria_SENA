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

COLOR_APRENDIZ   = HexColor('#39A900')
COLOR_INSTRUCTOR = HexColor('#7B1FA2')
COLOR_INVITADO   = HexColor('#FBC02D')
COLOR_ORGANIZADOR = HexColor('#455A64')

COLOR_SENA_VERDE_OSCURO = HexColor('#1F6B00')
GRIS_OSCURO = HexColor('#333333')

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

# ===========================================================
# COORDENADAS FIJAS sobre 107x135mm (0,0 = inf-izq)
# Ajustadas al layout del archivo Credencial.png:
# ===========================================================
POS_BADGE_ROL = {
    'x':      16 * mm,
    'y':      82 * mm,
    'w':      75 * mm,
    'h':      14 * mm,
    'r':      7 * mm,
    'dy_txt': 4.2 * mm,
    'size':   17,
}

POS_CAJA_NOMBRE = {
    'x':      11 * mm,
    'y':      53 * mm,
    'w':      85 * mm,
    'h':      27 * mm,
    'dy_txt': 11 * mm,
    'size':   17,
}

POS_CAJA_DOC = {
    'x':      31 * mm,
    'y':      41 * mm,
    'w':      45 * mm,
    'h':      10 * mm,
    'dy_txt': 2.8 * mm,
    'size':   11.5,
}

POS_CAJA_INFERIOR = {
    'x':      25 * mm,
    'y':      11 * mm,
    'w':      57 * mm,
    'h':      29 * mm,
    'size':   9,
    'size_1': 10.5,
}

POS_REVERSO_QR = {
    'x_c':    53.5 * mm,
    'y_c':    62 * mm,
    'w':      54 * mm,
}


class EscarapelaPDFService:
    W, H = ESCARAPELA_W, ESCARAPELA_H

    @staticmethod
    def _ruta_credencial():
        static_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / 'static']
        return Path(static_dirs[0]) / 'img' / 'Credencial.png'

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
            'codigo_proyecto': None,
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
        x = dx + POS_BADGE_ROL['x']
        y = dy + POS_BADGE_ROL['y']
        w = POS_BADGE_ROL['w']
        h = POS_BADGE_ROL['h']
        # Capa blanca opaca para TAPAR el badge verde original de la plantilla
        c.setFillColor(white)
        c.roundRect(x - 0.5 * mm, y - 0.5 * mm,
                    w + 1 * mm, h + 1 * mm,
                    POS_BADGE_ROL['r'], fill=1, stroke=0)
        # Badge color
        c.setFillColor(color_f)
        c.roundRect(x, y, w, h, POS_BADGE_ROL['r'], fill=1, stroke=0)
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
    def _caja_nombre(c, persona, dx=0, dy=0):
        texto = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar(
            c, texto,
            dy + POS_CAJA_NOMBRE['y'] + POS_CAJA_NOMBRE['dy_txt'],
            'Helvetica-Bold', POS_CAJA_NOMBRE['size'], black,
            POS_CAJA_NOMBRE['w'] - 4 * mm, dx,
        )

    @staticmethod
    def _caja_documento(c, persona, info, dx=0, dy=0):
        tipo = (info['tipo_identificacion'] or 'CC')
        num = info['numero_identificacion'] or ''
        txt = f'{tipo}  {num}'
        EscarapelaPDFService._centrar(
            c, txt,
            dy + POS_CAJA_DOC['y'] + POS_CAJA_DOC['dy_txt'],
            'Helvetica-Bold', POS_CAJA_DOC['size'], COLOR_SENA_VERDE_OSCURO,
            POS_CAJA_DOC['w'] - 4 * mm, dx,
        )

    @staticmethod
    def _caja_inferior(c, info, dx=0, dy=0):
        lineas = []
        if info['codigo_proyecto']:
            lineas.append(('Helvetica-Bold', POS_CAJA_INFERIOR['size_1'], info['codigo_proyecto'], COLOR_SENA_VERDE_OSCURO))
        if info['codigo_ficha']:
            lineas.append(('Helvetica', POS_CAJA_INFERIOR['size'], f'FICHA {info["codigo_ficha"]}', GRIS_OSCURO))
        if info['programa']:
            lineas.append(('Helvetica', POS_CAJA_INFERIOR['size'], info['programa'], GRIS_OSCURO))
        if info['institucion']:
            lineas.append(('Helvetica', POS_CAJA_INFERIOR['size'] - 0.5, info['institucion'], GRIS_OSCURO))
        if info['extra'] and not lineas:
            lineas.append(('Helvetica-Bold', POS_CAJA_INFERIOR['size_1'], info['extra'], COLOR_SENA_VERDE_OSCURO))
        if not lineas:
            return
        n = min(len(lineas), 4)
        paso = 6.4 * mm
        y_central = dy + POS_CAJA_INFERIOR['y'] + POS_CAJA_INFERIOR['h'] / 2
        y_inicio = y_central + paso * (n - 1) / 2
        for i in range(n):
            fuente, tam, txt, col = lineas[i]
            EscarapelaPDFService._centrar(
                c, txt, y_inicio - 2.8 * mm,
                fuente, tam, col, POS_CAJA_INFERIOR['w'] - 4 * mm, dx,
            )
            y_inicio -= paso

    @staticmethod
    def _dibujar_frente(c, persona, evento, dx=0, dy=0):
        info = EscarapelaPDFService._info_persona(persona)
        EscarapelaPDFService._dibujar_imagen_fondo(c, dx, dy)
        EscarapelaPDFService._badge_rol(c, persona.tipo_persona, dx, dy)
        EscarapelaPDFService._caja_nombre(c, persona, dx, dy)
        EscarapelaPDFService._caja_documento(c, persona, info, dx, dy)
        EscarapelaPDFService._caja_inferior(c, info, dx, dy)

    @staticmethod
    def _dibujar_reverso(c, persona, evento, dx=0, dy=0):
        W = EscarapelaPDFService.W
        H = EscarapelaPDFService.H
        c.setFillColor(white)
        c.rect(dx, dy, W, H, fill=1, stroke=0)
        # Banda sup verde 18mm
        b = 18 * mm
        c.setFillColor(COLOR_APRENDIZ)
        c.rect(dx, dy + H - b, W, b, fill=1, stroke=0)
        # Logo
        ruta_logo = EscarapelaPDFService._ruta_logo_sena()
        if ruta_logo.exists():
            try:
                from PIL import Image as PI
                with PI.open(ruta_logo) as im:
                    wi, he = im.size
                    al = 12 * mm
                    r = al / he
                    aw = wi * r
                cx = dx + W / 2
                cy = dy + H - b / 2
                c.drawImage(str(ruta_logo), cx - aw / 2, cy - al / 2, aw, al, mask='auto')
            except Exception:
                pass
        EscarapelaPDFService._centrar(
            c, 'IDENTIFICACIÓN DIGITAL · CÓDIGO ÚNICO',
            dy + H - 13 * mm,
            'Helvetica-Bold', 7.5, white, W - 10 * mm, dx
        )
        # QR
        qr_w = POS_REVERSO_QR['w']
        qr_x = dx + POS_REVERSO_QR['x_c'] - qr_w / 2
        qr_y = dy + POS_REVERSO_QR['y_c'] - qr_w / 2
        borde = BADGE_ROL_BORDE.get(persona.tipo_persona, COLOR_APRENDIZ)
        m = 3 * mm
        c.setStrokeColor(borde)
        c.setFillColor(HexColor('#FAFFF5'))
        c.setLineWidth(2.2)
        c.roundRect(qr_x - m, qr_y - m, qr_w + 2 * m, qr_w + 2 * m, 6 * mm, fill=1, stroke=1)
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        try:
            c.drawImage(ruta_qr, qr_x, qr_y, width=qr_w, height=qr_w, mask='auto')
        except Exception:
            pass
        # ID
        id_w = W - 24 * mm
        id_h = 8 * mm
        id_x = dx + (W - id_w) / 2
        id_y = qr_y - 11 * mm
        c.setStrokeColor(HexColor('#CCCCCC'))
        c.setFillColor(HexColor('#FAFCF4'))
        c.setLineWidth(1)
        c.roundRect(id_x, id_y, id_w, id_h, 3 * mm, fill=1, stroke=1)
        EscarapelaPDFService._centrar(
            c, f'ID: {persona.qr_token}',
            id_y + 2 * mm,
            'Helvetica', 7, COLOR_SENA_VERDE_OSCURO, id_w - 4 * mm, dx
        )
        # Nombre + rol
        nombre_txt = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar(
            c, nombre_txt, id_y - 8 * mm,
            'Helvetica-Bold', 9.2, black, W - 16 * mm, dx
        )
        color_rol = BADGE_ROL.get(persona.tipo_persona, BADGE_ROL['APRENDIZ'])[0]
        EscarapelaPDFService._centrar(
            c, BADGE_ROL_TEXTO.get(persona.tipo_persona, persona.tipo_persona or ''),
            id_y - 12.5 * mm,
            'Helvetica-Bold', 8, color_rol, W - 16 * mm, dx
        )
        # Footer verde
        f = 10 * mm
        c.setFillColor(COLOR_APRENDIZ)
        c.rect(dx, dy, W, f, fill=1, stroke=0)
        EscarapelaPDFService._centrar(
            c, 'VÁLIDO SOLO CON DOCUMENTO DE IDENTIDAD ORIGINAL · SENA · FERIA',
            dy + 3 * mm,
            'Helvetica-Bold', 6.8, white, W - 10 * mm, dx
        )

    @staticmethod
    def _renderizar_persona(c, persona, evento, dx=0, dy=0):
        EscarapelaPDFService._dibujar_frente(c, persona, evento, dx, dy)
        c.showPage()
        EscarapelaPDFService._dibujar_reverso(c, persona, evento, dx, dy)
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
            EscarapelaPDFService._bloques_carta(c, personas, evento, EscarapelaPDFService._dibujar_reverso)
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
