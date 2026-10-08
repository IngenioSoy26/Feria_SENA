import io
from pathlib import Path

from django.conf import settings

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase import pdfmetrics

from apps.personas.services import QrService


ESCARAPELA_W = 107 * mm
ESCARAPELA_H = 135 * mm
CARTA_W, CARTA_H = letter
GUTTER = 1.5 * mm

COLOR_SENA_VERDE = HexColor('#39A900')
COLOR_SENA_VERDE_OSCURO = HexColor('#1F6B00')
COLOR_SENA_VERDE_MEDIO = HexColor('#2E8A00')
COLOR_SENA_AZUL = HexColor('#0067B1')
COLOR_SENA_NARANJA = HexColor('#F57C00')
COLOR_SENA_AMARILLO = HexColor('#FFC107')

COLOR_APRENDIZ = COLOR_SENA_VERDE
COLOR_INSTRUCTOR = HexColor('#7B1FA2')
COLOR_INVITADO = HexColor('#FBC02D')
COLOR_ORGANIZADOR = HexColor('#455A64')

COLOR_ROL_BADGE = {
    'APRENDIZ': (COLOR_APRENDIZ, white),
    'INSTRUCTOR': (COLOR_INSTRUCTOR, white),
    'INVITADO': (COLOR_INVITADO, black),
    'ORGANIZADOR': (COLOR_ORGANIZADOR, white),
}
COLOR_ROL_BORDE = {
    'APRENDIZ': COLOR_APRENDIZ,
    'INSTRUCTOR': COLOR_INSTRUCTOR,
    'INVITADO': COLOR_INVITADO,
    'ORGANIZADOR': COLOR_ORGANIZADOR,
}
ETIQUETAS_ROL = {
    'APRENDIZ': 'APRENDIZ',
    'INSTRUCTOR': 'INSTRUCTOR',
    'INVITADO': 'INVITADO',
    'ORGANIZADOR': 'ORGANIZADOR',
}

BG_BEIGE = HexColor('#FFF8E7')
BG_CIELO = HexColor('#E3F2FD')
BG_DESIERTO_CLARO = HexColor('#FFE0B2')
BG_DESIERTO_OSCURO = HexColor('#FFAB91')
BG_MAR = HexColor('#4FC3F7')
BG_MONTAÑA = HexColor('#90CAF9')
BG_TIERRA = HexColor('#FFCC80')

GRIS_TEXTO = HexColor('#444444')
GRIS_TEXTO_SUAVE = HexColor('#666666')
GRIS_BORDE = HexColor('#CCCCCC')


def _color_rol_fondo(rol):
    return COLOR_ROL_BADGE.get(rol, COLOR_ROL_BADGE['APRENDIZ'])[0]


def _color_rol_texto(rol):
    return COLOR_ROL_BADGE.get(rol, COLOR_ROL_BADGE['APRENDIZ'])[1]


def _color_rol_borde(rol):
    return COLOR_ROL_BORDE.get(rol, COLOR_SENA_VERDE)


class EscarapelaPDFService:
    W, H = ESCARAPELA_W, ESCARAPELA_H

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
    def _centrar_texto(c, texto, y, fuente, tamano, color=None, max_w=None, dx=0, dy=0):
        if color is None:
            color = black
        if max_w is None:
            max_w = EscarapelaPDFService.W - 8 * mm
        ancho = c.stringWidth(texto, fuente, tamano)
        if ancho > max_w and tamano > 6:
            return EscarapelaPDFService._centrar_texto(c, texto, y, fuente, tamano - 1, color, max_w, dx, dy)
        c.setFillColor(color)
        c.setFont(fuente, tamano)
        x = dx + (EscarapelaPDFService.W - ancho) / 2
        c.drawString(x, y + dy, texto)
        return x, y + dy, ancho

    @staticmethod
    def _draw_image(c, ruta, x_c, y_c, alto_max, dx=0, dy=0):
        ruta_p = Path(ruta)
        if not ruta_p.exists():
            return
        try:
            from PIL import Image as PILImage
            with PILImage.open(ruta_p) as img:
                wi, he = img.size
                r = alto_max / he
                ancho = wi * r
            x0 = dx + x_c - ancho / 2
            y0 = dy + y_c - alto_max / 2
            c.drawImage(str(ruta_p), x0, y0, width=ancho, height=alto_max, mask='auto')
        except Exception:
            pass

    # ===========================================================
    # FONDO GRÁFICO (banda superior SENA + desierto inferior)
    # ===========================================================
    @staticmethod
    def _dibujar_fondo_base(c, dx=0, dy=0):
        W = EscarapelaPDFService.W
        H = EscarapelaPDFService.H

        # --- Fondo general beige suave ---
        c.setFillColor(BG_BEIGE)
        c.rect(dx, dy, W, H, fill=1, stroke=0)

        # --- CIELO (franja superior 60mm, gradiente suave simulado 3 bandas) ---
        cielo_alto = 60 * mm
        c.setFillColor(HexColor('#E1F5FE'))
        c.rect(dx, dy + H - cielo_alto, W, cielo_alto, fill=1, stroke=0)
        c.setFillColor(HexColor('#B3E5FC'))
        c.rect(dx, dy + H - cielo_alto, W, 1.2 * mm, fill=1, stroke=0)

        # --- CÍRCULO VERDE ESQUINA SUPERIOR IZQUIERDA (logo SENA) ---
        r = 34 * mm
        c.setFillColor(COLOR_SENA_VERDE_OSCURO)
        c.circle(dx + 0 * mm, dy + H, r, fill=1, stroke=0)
        c.setFillColor(COLOR_SENA_VERDE)
        c.circle(dx - 3 * mm, dy + H - 3 * mm, r - 6 * mm, fill=1, stroke=0)

        # --- HUECO DE PASANTE (arriba centro, oval decorativo) ---
        hueco_w = 34 * mm
        hueco_h = 7 * mm
        hueco_x = dx + (W - hueco_w) / 2
        hueco_y = dy + H - 17 * mm
        c.setFillColor(white)
        c.roundRect(hueco_x, hueco_y, hueco_w, hueco_h, 3.5 * mm, fill=1, stroke=0)
        c.setStrokeColor(HexColor('#BDBDBD'))
        c.setLineWidth(0.5)
        c.roundRect(hueco_x, hueco_y, hueco_w, hueco_h, 3.5 * mm, fill=0, stroke=1)

        # --- BANDA INFERIOR: MONTAÑAS / DESIERTO / MAR / CACTUS SIMPLIFICADOS ---
        base_y = dy + 0 * mm
        alt_bandas = 46 * mm
        # Tierra / mar
        c.setFillColor(BG_TIERRA)
        c.rect(dx, dy, W, alt_bandas, fill=1, stroke=0)
        # Mar (franja derecha inferior)
        c.setFillColor(BG_MAR)
        c.rect(dx + W * 0.55, dy, W * 0.45, 16 * mm, fill=1, stroke=0)
        # Mar claro (orilla)
        c.setFillColor(HexColor('#81D4FA'))
        c.rect(dx + W * 0.55, dy + 10 * mm, W * 0.45, 8 * mm, fill=1, stroke=0)
        # Sol amarillo (esquina inferior derecha)
        c.setFillColor(HexColor('#FFD54F'))
        c.circle(dx + W - 22 * mm, dy + 34 * mm, 11 * mm, fill=1, stroke=0)
        # Montañas azul (traseras, encima del mar)
        c.setFillColor(BG_MONTAÑA)
        p = c.beginPath()
        p.moveTo(dx + W * 0.4, dy + 18 * mm)
        p.lineTo(dx + W * 0.6, dy + 33 * mm)
        p.lineTo(dx + W * 0.85, dy + 18 * mm)
        p.lineTo(dx + W, dy + 18 * mm)
        p.lineTo(dx + W, dy + 10 * mm)
        p.lineTo(dx + W * 0.4, dy + 10 * mm)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        # Colinas desierto
        c.setFillColor(BG_DESIERTO_CLARO)
        p2 = c.beginPath()
        p2.moveTo(dx, dy + 10 * mm)
        p2.curveTo(dx + W * 0.2, dy + 28 * mm,
                   dx + W * 0.5, dy + 22 * mm,
                   dx + W * 0.55, dy + 18 * mm)
        p2.lineTo(dx + W * 0.55, dy)
        p2.lineTo(dx, dy)
        p2.close()
        c.drawPath(p2, fill=1, stroke=0)
        # Cactus (siluetas)
        def _cactus(x_base, y_base, h, dx_o, dy_o):
            # Verde cactus
            c.setFillColor(HexColor('#2E7D32'))
            # Cuerpo principal
            c.rect(dx_o + x_base, dy_o + y_base, 3 * mm, h, fill=1, stroke=0)
            # Brazo izq
            c.rect(dx_o + x_base - 2 * mm, dy_o + y_base + h * 0.35, 2 * mm, 1.2 * mm, fill=1, stroke=0)
            c.rect(dx_o + x_base - 2 * mm, dy_o + y_base + h * 0.35, 1 * mm, h * 0.3, fill=1, stroke=0)
            # Brazo der
            c.rect(dx_o + x_base + 3 * mm, dy_o + y_base + h * 0.5, 2 * mm, 1.2 * mm, fill=1, stroke=0)
            c.rect(dx_o + x_base + 4 * mm, dy_o + y_base + h * 0.5, 1 * mm, h * 0.25, fill=1, stroke=0)

        _cactus(9 * mm, 8 * mm, 22 * mm, dx, dy)
        _cactus(16 * mm, 2 * mm, 14 * mm, dx, dy)
        _cactus(W - 14 * mm, 5 * mm, 15 * mm, dx, dy)
        _cactus(W - 21 * mm, 11 * mm, 9 * mm, dx, dy)

        # Pajitas/plantas pequeñas
        c.setFillColor(HexColor('#43A047'))
        for xp in [24 * mm, 33 * mm, W - 30 * mm, W - 38 * mm]:
            hh = 4 * mm
            c.rect(dx + xp, dy + 4 * mm, 0.8 * mm, hh, fill=1, stroke=0)
            c.rect(dx + xp - 1.2 * mm, dy + 6 * mm, 1.2 * mm, 0.6 * mm, fill=1, stroke=0)
            c.rect(dx + xp + 0.8 * mm, dy + 7 * mm, 1.2 * mm, 0.6 * mm, fill=1, stroke=0)

        # Pájaros (dos V)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        for bx, by in [(W - 20 * mm, 90 * mm), (W - 11 * mm, 84 * mm)]:
            p3 = c.beginPath()
            p3.moveTo(dx + bx - 2.5 * mm, dy + by)
            p3.lineTo(dx + bx, dy + by + 1.4 * mm)
            p3.lineTo(dx + bx + 2.5 * mm, dy + by)
            c.drawPath(p3, fill=0, stroke=1)

        # Panel solar (esquina inf-izq, sobre el desierto)
        c.setFillColor(HexColor('#1976D2'))
        ps_x, ps_y = dx + 4 * mm, dy + 22 * mm
        c.saveState()
        c.translate(ps_x + 5 * mm, ps_y + 6 * mm)
        c.rotate(-0.25)
        c.rect(-5 * mm, -4 * mm, 10 * mm, 8 * mm, fill=1, stroke=0)
        c.setStrokeColor(white)
        c.setLineWidth(0.3)
        c.line(-5 * mm, -1.3 * mm, 5 * mm, -1.3 * mm)
        c.line(-5 * mm, 1.3 * mm, 5 * mm, 1.3 * mm)
        c.line(-1.6 * mm, -4 * mm, -1.6 * mm, 4 * mm)
        c.line(1.6 * mm, -4 * mm, 1.6 * mm, 4 * mm)
        c.restoreState()
        # Poste
        c.setStrokeColor(HexColor('#616161'))
        c.setLineWidth(0.7)
        c.line(ps_x + 5 * mm, ps_y + 2 * mm, ps_x + 5 * mm, dy + 2 * mm)
        # Sol pequeño (arriba de panel)
        c.setFillColor(HexColor('#FFB300'))
        c.circle(ps_x + 1 * mm, ps_y + 9 * mm, 2.6 * mm, fill=1, stroke=0)
        # Rayos sol
        c.setStrokeColor(HexColor('#FFB300'))
        c.setLineWidth(0.5)
        for ang in range(0, 360, 45):
            import math
            a = ang * 3.14159 / 180
            x1 = ps_x + 1 * mm + math.cos(a) * 3.2 * mm
            y1 = ps_y + 9 * mm + math.sin(a) * 3.2 * mm
            x2 = ps_x + 1 * mm + math.cos(a) * 4.2 * mm
            y2 = ps_y + 9 * mm + math.sin(a) * 4.2 * mm
            c.line(x1, y1, x2, y2)

    @staticmethod
    def _dibujar_titulo_evento(c, evento, dx=0, dy=0):
        W = EscarapelaPDFService.W
        H = EscarapelaPDFService.H
        # Logo SENA sobre círculo verde
        EscarapelaPDFService._draw_image(c, EscarapelaPDFService._ruta_logo_sena(),
                                          26 * mm, H - 22 * mm, 18 * mm, dx, dy)
        # Título "SENA" al lado del logo
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 13)
        c.drawString(dx + 7 * mm, dy + H - 26 * mm, 'SENA')

        # --- TÍTULO PRINCIPAL ---
        titulo_y = H - 38 * mm
        # "VI Feria de"
        EscarapelaPDFService._centrar_texto(c, 'VI Feria de',
                                            dy + titulo_y + 9 * mm, 'Helvetica-Bold', 22, black,
                                            max_w=W - 10 * mm, dx=dx)
        # "Proyectos Productivos" (verde + azul)
        # Medir verde "Proyectos " y azul "Productivos" y juntar centrados
        f1, t1, s1 = 'Helvetica-Bold', 'PROYECTOS ', 20
        f2, t2, s2 = 'Helvetica-Bold', 'PRODUCTIVOS', 20
        ancho1 = c.stringWidth(t1, f1, s1)
        ancho2 = c.stringWidth(t2, f2, s2)
        ancho_t = ancho1 + ancho2
        x1 = dx + (W - ancho_t) / 2
        x2 = x1 + ancho1
        c.setFillColor(COLOR_SENA_VERDE)
        c.setFont(f1, s1)
        c.drawString(x1, dy + titulo_y, t1)
        c.setFillColor(COLOR_SENA_AZUL)
        c.setFont(f2, s2)
        c.drawString(x2, dy + titulo_y, t2)

        # Raya 3 colores (verde/naranja/amarillo)
        ry = titulo_y - 4 * mm
        r_ancho = W - 18 * mm
        r_x = dx + (W - r_ancho) / 2
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(r_x, dy + ry, r_ancho * 0.33, 1.6 * mm, fill=1, stroke=0)
        c.setFillColor(COLOR_SENA_NARANJA)
        c.rect(r_x + r_ancho * 0.33, dy + ry, r_ancho * 0.34, 1.6 * mm, fill=1, stroke=0)
        c.setFillColor(COLOR_SENA_AMARILLO)
        c.rect(r_x + r_ancho * 0.67, dy + ry, r_ancho * 0.33, 1.6 * mm, fill=1, stroke=0)

        # 3 rayitas (petalos estilo logo)
        sx_c = dx + W - 27 * mm
        sy_c = dy + H - 33 * mm
        colores_p = [COLOR_SENA_VERDE, COLOR_SENA_NARANJA, COLOR_SENA_AMARILLO]
        for i, col in enumerate(colores_p):
            c.setFillColor(col)
            c.circle(sx_c - 4 * mm + i * 4 * mm, sy_c + (3 if i == 1 else 0) * mm,
                     2.2 * mm, fill=1, stroke=0)

        # Subtítulo 1
        sub1 = evento.subtitulo if (evento and hasattr(evento, 'subtitulo') and evento.subtitulo) else \
            'Programa de Articulación con la Educación Media del SENA'
        EscarapelaPDFService._centrar_texto(c, sub1,
                                            dy + ry - 7 * mm,
                                            'Helvetica-Bold', 9, COLOR_SENA_AZUL,
                                            max_w=W - 16 * mm, dx=dx)
        # Subtítulo 2
        sub2 = evento.lugar if (evento and evento.lugar) else \
            'CENTRO INDUSTRIAL Y DE ENERGÍAS ALTERNATIVAS - 2026'
        EscarapelaPDFService._centrar_texto(c, sub2,
                                            dy + ry - 12 * mm,
                                            'Helvetica-Bold', 8.2, COLOR_SENA_VERDE_OSCURO,
                                            max_w=W - 18 * mm, dx=dx)

    @staticmethod
    def _dibujar_badge_rol(c, rol, y_centro, dx=0, dy=0):
        W = EscarapelaPDFService.W
        color_f = _color_rol_fondo(rol)
        color_t = _color_rol_texto(rol)
        texto = ETIQUETAS_ROL.get(rol, rol or '')
        ancho = 74 * mm
        alto = 13 * mm
        x = dx + (W - ancho) / 2
        y = dy + y_centro - alto / 2
        c.setFillColor(color_f)
        c.roundRect(x, y, ancho, alto, 6 * mm, fill=1, stroke=0)
        # Borde sutil
        c.setStrokeColor(HexColor('#000000'))
        c.setStrokeAlpha(0.15)
        c.setLineWidth(0.5)
        c.roundRect(x, y, ancho, alto, 6 * mm, fill=0, stroke=1)
        c.setStrokeAlpha(1)
        EscarapelaPDFService._centrar_texto(c, texto,
                                            dy + y_centro - 4.2 * mm,
                                            'Helvetica-Bold', 16, color_t,
                                            max_w=ancho - 8 * mm, dx=dx)

    @staticmethod
    def _caja_borde_redondo(c, x, y, w, h, radio, color_borde, grosor=2.2, fill=white):
        c.setFillColor(fill)
        c.setStrokeColor(color_borde)
        c.setLineWidth(grosor)
        c.roundRect(x, y, w, h, radio, fill=1, stroke=1)

    @staticmethod
    def _dibujar_frente(c, persona, evento, dx=0, dy=0):
        W = EscarapelaPDFService.W
        H = EscarapelaPDFService.H

        # 1) Fondo gráfico completo
        EscarapelaPDFService._dibujar_fondo_base(c, dx, dy)

        # 2) Título + logo
        EscarapelaPDFService._dibujar_titulo_evento(c, evento, dx, dy)

        # 3) Badge ROL
        badge_y = H - 65 * mm
        EscarapelaPDFService._dibujar_badge_rol(c, persona.tipo_persona, badge_y, dx, dy)

        rol_borde = _color_rol_borde(persona.tipo_persona)

        # 4) CAJA NOMBRE (grande, arriba del badge)
        caja_nom_w = W - 14 * mm
        caja_nom_h = 30 * mm
        caja_nom_x = dx + (W - caja_nom_w) / 2
        caja_nom_y = dy + badge_y - caja_nom_h - 6 * mm
        EscarapelaPDFService._caja_borde_redondo(c, caja_nom_x, caja_nom_y, caja_nom_w, caja_nom_h, 8 * mm, rol_borde, 2.4)
        # Nombre completo (grande)
        EscarapelaPDFService._centrar_texto(c,
                                            (persona.nombre_completo or '').upper(),
                                            caja_nom_y + caja_nom_h / 2 - 5 * mm,
                                            'Helvetica-Bold', 17, black,
                                            max_w=caja_nom_w - 10 * mm, dx=dx, dy=0)

        # 5) CAJA DOCUMENTO (más pequeña, entre caja nombre y foto)
        caja_doc_w = W - 36 * mm
        caja_doc_h = 11 * mm
        caja_doc_x = dx + (W - caja_doc_w) / 2
        caja_doc_y = caja_nom_y - caja_doc_h - 6 * mm
        EscarapelaPDFService._caja_borde_redondo(c, caja_doc_x, caja_doc_y, caja_doc_w, caja_doc_h, 5 * mm, rol_borde, 2.2)
        info = EscarapelaPDFService._info_persona(persona)
        tipo_doc = (info['tipo_identificacion'] or 'CC')
        num_doc = info['numero_identificacion'] or ''
        doc_txt = f'{tipo_doc}:  {num_doc}'
        EscarapelaPDFService._centrar_texto(c, doc_txt,
                                            caja_doc_y + 2.8 * mm,
                                            'Helvetica-Bold', 11, COLOR_SENA_VERDE_OSCURO,
                                            max_w=caja_doc_w - 6 * mm, dx=dx)

        # 6) CAJA FOTO/QR (inferior, grande, sobre el desierto)
        caja_foto_w = W - 34 * mm
        caja_foto_h = 36 * mm
        caja_foto_x = dx + (W - caja_foto_w) / 2
        caja_foto_y = dy + 8 * mm
        EscarapelaPDFService._caja_borde_redondo(c, caja_foto_x, caja_foto_y, caja_foto_w, caja_foto_h, 10 * mm, rol_borde, 2.6)

        # Dentro: Proyecto/Ficha/Institucion/Programa multilinea
        lineas_extra = []
        if info['codigo_proyecto']:
            lineas_extra.append(f'PROYECTO: {info["codigo_proyecto"]}')
        if info['codigo_ficha']:
            lineas_extra.append(f'FICHA: {info["codigo_ficha"]}')
        if info['programa']:
            lineas_extra.append(info['programa'])
        if info['institucion']:
            lineas_extra.append(info['institucion'])
        if info['extra'] and not lineas_extra:
            lineas_extra.append(info['extra'])
        if not lineas_extra:
            lineas_extra.append('')
        # Dibujar centrado verticalmente dentro de caja
        n = min(len(lineas_extra), 4)
        start_y = caja_foto_y + caja_foto_h / 2 + (n - 1) * 2.2 * mm
        for i in range(n):
            linea = lineas_extra[i]
            if i == 0 and lineas_extra:
                fuente, tam, col = 'Helvetica-Bold', 10.5, COLOR_SENA_VERDE_OSCURO
            else:
                fuente, tam, col = 'Helvetica', 8.2, GRIS_TEXTO
            EscarapelaPDFService._centrar_texto(c, linea,
                                                start_y - 4.5 * mm,
                                                fuente, tam, col,
                                                max_w=caja_foto_w - 10 * mm, dx=dx)
            start_y -= 4.5 * mm

    @staticmethod
    def _dibujar_reverso(c, persona, evento, dx=0, dy=0):
        W = EscarapelaPDFService.W
        H = EscarapelaPDFService.H
        # Fondo reverso: blanco liso con banda superior/inferior
        c.setFillColor(white)
        c.rect(dx, dy, W, H, fill=1, stroke=0)

        # Banda superior verde
        banda_alto = 18 * mm
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(dx, dy + H - banda_alto, W, banda_alto, fill=1, stroke=0)
        # Logo SENA
        EscarapelaPDFService._draw_image(c, EscarapelaPDFService._ruta_logo_sena(),
                                          W / 2, H - banda_alto / 2, 12 * mm, dx, dy)
        # Texto bajo logo
        EscarapelaPDFService._centrar_texto(c, 'IDENTIFICACIÓN DIGITAL · CÓDIGO ÚNICO',
                                            dy + H - 13 * mm,
                                            'Helvetica-Bold', 7.5, white,
                                            max_w=W - 10 * mm, dx=dx)

        # QR grande centrado
        qr_size = 54 * mm
        qr_x = dx + (W - qr_size) / 2
        qr_y = dy + (H - qr_size) / 2 - 4 * mm
        # Caja QR (borde color rol)
        rol_borde = _color_rol_borde(persona.tipo_persona)
        EscarapelaPDFService._caja_borde_redondo(c, qr_x - 3 * mm, qr_y - 3 * mm,
                                                  qr_size + 6 * mm, qr_size + 6 * mm,
                                                  6 * mm, rol_borde, 2.2,
                                                  fill=HexColor('#FAFFF5'))
        ruta_qr = QrService.asegurarse_qr_existe(persona)
        try:
            c.drawImage(ruta_qr, qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')
        except Exception:
            c.setStrokeColor(GRIS_BORDE)
            c.setFillColor(HexColor('#f5f5f5'))
            c.rect(qr_x, qr_y, qr_size, qr_size, fill=1, stroke=1)

        # ID UUID
        id_ancho = W - 24 * mm
        id_alto = 8 * mm
        id_x = dx + (W - id_ancho) / 2
        id_y = qr_y - 11 * mm
        EscarapelaPDFService._caja_borde_redondo(c, id_x, id_y, id_ancho, id_alto,
                                                  3 * mm, GRIS_BORDE, 1,
                                                  fill=HexColor('#FAFCF4'))
        EscarapelaPDFService._centrar_texto(c, f'ID: {persona.qr_token}',
                                            id_y + 2 * mm,
                                            'Helvetica', 7, COLOR_SENA_VERDE_OSCURO,
                                            max_w=id_ancho - 4 * mm, dx=dx)

        # Nombre + rol bajo ID
        info = EscarapelaPDFService._info_persona(persona)
        color_rol = _color_rol_fondo(persona.tipo_persona)
        nombre_txt = (persona.nombre_completo or '').upper()
        EscarapelaPDFService._centrar_texto(c, nombre_txt,
                                            id_y - 8 * mm,
                                            'Helvetica-Bold', 9.2, black,
                                            max_w=W - 16 * mm, dx=dx)
        rol_txt = ETIQUETAS_ROL.get(persona.tipo_persona, persona.tipo_persona or '')
        EscarapelaPDFService._centrar_texto(c, rol_txt,
                                            id_y - 12.5 * mm,
                                            'Helvetica-Bold', 8, color_rol,
                                            max_w=W - 16 * mm, dx=dx)

        # Footer verde
        footer_alto = 10 * mm
        c.setFillColor(COLOR_SENA_VERDE)
        c.rect(dx, dy, W, footer_alto, fill=1, stroke=0)
        leyenda = 'VÁLIDO SOLO CON DOCUMENTO DE IDENTIDAD ORIGINAL · SENA · FERIA'
        EscarapelaPDFService._centrar_texto(c, leyenda,
                                            dy + 3 * mm,
                                            'Helvetica-Bold', 6.8, white,
                                            max_w=W - 10 * mm, dx=dx)

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
    def _posiciones_grid_carta():
        """Devuelve 4 slots (dx, dy) en p. CARTA: 2 cols × 2 filas. dy es y_inf slot (ReportLab coord inf-izq)."""
        slots = []
        for fila in (1, 0):  # fila 1 = arriba, fila 0 = abajo
            for col in (0, 1):
                dx = (CARTA_W - 2 * EscarapelaPDFService.W - GUTTER) / 2 + col * (EscarapelaPDFService.W + GUTTER)
                dy = (CARTA_H - 2 * EscarapelaPDFService.H - GUTTER) / 2 + fila * (EscarapelaPDFService.H + GUTTER)
                slots.append((dx, dy))
        return slots

    @staticmethod
    def _renderizar_lote_carta(c, personas, evento, fn_pagina):
        """fn_pagina = _dibujar_frente o _dibujar_reverso. Dibuja bloques de 4 por hoja CARTA."""
        slots = EscarapelaPDFService._posiciones_grid_carta()
        for i in range(0, len(personas), 4):
            grupo = personas[i:i + 4]
            for idx, p in enumerate(grupo):
                dx, dy = slots[idx]
                # Guarda estado para no heredar rotaciones/colores
                c.saveState()
                fn_pagina(c, p, evento, dx, dy)
                c.restoreState()
            c.showPage()

    @staticmethod
    def generar_lote(qs_personas, evento, titulo_lote=None, formato='CARTA_4X'):
        """
        formato:
          - 'CARTA_4X' (default): hojas CARTA con 4 escarapelas por hoja. Primero TODOS los frentes (4x hoja),
            luego TODOS los reversos (4x hoja) para impresión dúplex.
          - 'INDIVIDUAL' (antiguo): 107x135mm individual dúplex 2 páginas/persona.
        """
        personas = list(qs_personas)
        buffer = io.BytesIO()
        if formato == 'INDIVIDUAL':
            c = canvas.Canvas(buffer, pagesize=(EscarapelaPDFService.W, EscarapelaPDFService.H))
            for p in personas:
                EscarapelaPDFService._renderizar_persona(c, p, evento)
        else:
            c = canvas.Canvas(buffer, pagesize=letter)
            # Bloque 1: TODOS los frentes (4 por hoja CARTA)
            EscarapelaPDFService._renderizar_lote_carta(c, personas, evento, EscarapelaPDFService._dibujar_frente)
            # Bloque 2: TODOS los reversos (mismo orden, 4 por hoja CARTA)
            EscarapelaPDFService._renderizar_lote_carta(c, personas, evento, EscarapelaPDFService._dibujar_reverso)
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generar_por_proyecto(proyecto, formato='CARTA_4X'):
        from apps.personas.models import Persona
        evento = proyecto.evento
        qs = Persona.objects.filter(
            perfil_aprendiz__proyecto=proyecto,
            activo=True,
        ).order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'Proyecto {proyecto.codigo}', formato=formato)

    @staticmethod
    def generar_por_institucion(ie, evento, formato='CARTA_4X'):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto
        proyectos_ie = Proyecto.objects.filter(institucion=ie, evento=evento).values_list('id', flat=True)
        qs = Persona.objects.filter(
            perfil_aprendiz__proyecto_id__in=list(proyectos_ie),
            activo=True,
        ).order_by('apellidos', 'nombres')
        return EscarapelaPDFService.generar_lote(qs, evento, f'Institución {ie.codigo}', formato=formato)

    @staticmethod
    def generar_por_programa(programa, evento, formato='CARTA_4X'):
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
        return EscarapelaPDFService.generar_lote(qs, evento, f'Programa {programa.codigo}', formato=formato)

    @staticmethod
    def generar_completo(evento, formato='CARTA_4X'):
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
        return EscarapelaPDFService.generar_lote(qs, evento, 'Completo', formato=formato)
