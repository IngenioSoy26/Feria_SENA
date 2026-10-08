import io
from pathlib import Path

from PIL import Image, ImageOps
from django.conf import settings
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from apps.personas.services import QrService


# ============================================================
# DIMENSIONES FÍSICAS
# ============================================================
# Porta-escarapela: 10.7 cm x 13.5 cm
ESCARAPELA_W = 107 * mm
ESCARAPELA_H = 135 * mm

CARTA_W, CARTA_H = letter

# En carta caben 2 x 2. Gutter 3mm mínimo garantiza margen de corte
# para gillotina/tijera al imprimir 4 tarjetas por hoja.
GUTTER = 3.0 * mm


# ============================================================
# COLORES
# ============================================================
COLOR_APRENDIZ = HexColor("#39A900")
COLOR_INSTRUCTOR = HexColor("#71277A")
COLOR_INVITADO = HexColor("#FDC300")
COLOR_ORGANIZADOR = HexColor("#00304D")

COLOR_SENA_VERDE_OSCURO = HexColor("#007832")
GRIS_OSCURO = HexColor("#222222")
GRIS_MEDIO = HexColor("#444444")


BADGE_ROL = {
    "APRENDIZ": (COLOR_APRENDIZ, white),
    "INSTRUCTOR": (COLOR_INSTRUCTOR, white),
    "INVITADO": (COLOR_INVITADO, black),
    "ORGANIZADOR": (COLOR_ORGANIZADOR, white),
}

BADGE_ROL_TEXTO = {
    "APRENDIZ": "APRENDIZ",
    "INSTRUCTOR": "INSTRUCTOR",
    "INVITADO": "INVITADO",
    "ORGANIZADOR": "ORGANIZADOR",
}


# ============================================================
# MAQUETACIÓN
# 0,0 = esquina inferior izquierda.
#
# La plantilla PNG debe contener únicamente:
# - Logo SENA
# - Título de la feria
# - Programa / Centro
# - Paisaje / fondo
#
# Python dibuja:
# - Rol
# - Nombre
# - Institución
# - Documento
# - Proyecto
# - QR
#
# NO se muestra municipio.
# ============================================================

POS_BADGE = {
    "x": 18 * mm,
    "y": 91.5 * mm,
    "w": 71 * mm,
    "h": 8.5 * mm,
    "r": 4.25 * mm,
    "size": 12.5,
}


POS_CAJA_NOMBRE = {
    "x": 7 * mm,
    "y": 70 * mm,
    "w": 93 * mm,
    "h": 18.5 * mm,
    "r": 6 * mm,
    "borde_grosor": 1.0,
    "padding_lados": 5 * mm,

    # Baselines
    "y_nombre": 81.7 * mm,
    "y_institucion": 74.7 * mm,

    "size_nombre": 14,
    "size_institucion": 8.2,
}


POS_CAJA_DOC = {
    "x": 27 * mm,
    "y": 60.3 * mm,
    "w": 53 * mm,
    "h": 6.8 * mm,
    "r": 3.4 * mm,
    "borde_grosor": 0.9,
    "y_texto": 62.45 * mm,
    "size": 9.5,
}


POS_CAJA_INFERIOR = {
    "x": 9 * mm,
    "y": 8 * mm,
    "w": 89 * mm,
    "h": 48.5 * mm,
    "r": 6 * mm,
    "borde_grosor": 1.1,

    # Proyecto
    "y_proyecto_1": 51.0 * mm,
    "y_proyecto_2": 46.7 * mm,
    "size_label": 8.0,
    "size_valor": 8.6,

    # QR
    "qr_size": 31.5 * mm,
    "qr_centro_x": 53.5 * mm,
    "qr_y_inf": 11.0 * mm,
}


class EscarapelaPDFService:
    W = ESCARAPELA_W
    H = ESCARAPELA_H

    # ========================================================
    # RUTAS / DATOS
    # ========================================================

    @staticmethod
    def _ruta_credencial():
        static_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / "static"]
        return Path(static_dirs[0]) / "img" / "Credencial.png"

    @staticmethod
    def _info_persona(persona):
        """
        Devuelve solamente la información que realmente se imprime.
        Se elimina municipio de la composición.
        """
        info = {
            "institucion": None,
            "programa": None,
            "proyecto": None,
            "extra": None,
            "codigo_ficha": None,
            "tipo_identificacion": None,
            "numero_identificacion": None,
            "codigo_proyecto": None,
        }

        try:
            if persona.tipo_identificacion:
                info["tipo_identificacion"] = (
                    persona.tipo_identificacion.abreviatura or ""
                ).upper()
        except Exception:
            pass

        info["numero_identificacion"] = persona.numero_identificacion or ""

        if persona.tipo_persona == "APRENDIZ":
            perfil = getattr(persona, "perfil_aprendiz", None)

            if perfil and perfil.proyecto:
                proyecto = perfil.proyecto

                info["proyecto"] = proyecto.nombre
                info["codigo_proyecto"] = getattr(proyecto, "codigo", None)

                if proyecto.institucion:
                    info["institucion"] = proyecto.institucion.nombre

                if proyecto.programa:
                    info["programa"] = proyecto.programa.nombre

                if proyecto.ficha:
                    info["codigo_ficha"] = proyecto.ficha.numero

        elif persona.tipo_persona == "INSTRUCTOR":
            perfil = getattr(persona, "perfil_instructor", None)

            if perfil:
                programas = list(perfil.programas.all()[:2])

                if programas:
                    info["programa"] = " · ".join(
                        p.nombre for p in programas
                    )

                info["extra"] = "INSTRUCTOR SENA"

        elif persona.tipo_persona == "INVITADO":
            perfil = getattr(persona, "perfil_invitado", None)

            if perfil:
                info["institucion"] = perfil.entidad
                info["extra"] = perfil.cargo

        elif persona.tipo_persona == "ORGANIZADOR":
            info["extra"] = "ORGANIZADOR"

        return info

    # ========================================================
    # UTILIDADES DE TEXTO
    # ========================================================

    @staticmethod
    def _centrar_en_caja(
        c,
        texto,
        caja_x,
        caja_w,
        y,
        fuente,
        tam,
        color,
        max_w=None,
        tam_min=6,
    ):
        """
        Centra horizontalmente dentro de una caja concreta.
        Reduce tamaño de fuente si el texto no cabe.
        """
        texto = str(texto or "").strip()

        if not texto:
            return

        if max_w is None:
            max_w = caja_w

        ancho = c.stringWidth(texto, fuente, tam)

        while ancho > max_w and tam > tam_min:
            tam -= 0.5
            ancho = c.stringWidth(texto, fuente, tam)

        c.setFillColor(color)
        c.setFont(fuente, tam)

        x = caja_x + (caja_w - ancho) / 2
        c.drawString(x, y, texto)

    @staticmethod
    def _partir_texto_dos_lineas(c, texto, fuente, tam, max_w):
        """
        Parte un texto largo en máximo 2 líneas procurando separar por palabras.
        """
        texto = " ".join(str(texto or "").split())

        if not texto:
            return "", ""

        if c.stringWidth(texto, fuente, tam) <= max_w:
            return texto, ""

        palabras = texto.split()
        mejor_1 = ""
        mejor_2 = texto

        for i in range(1, len(palabras)):
            l1 = " ".join(palabras[:i])
            l2 = " ".join(palabras[i:])

            if (
                c.stringWidth(l1, fuente, tam) <= max_w
                and c.stringWidth(l2, fuente, tam) <= max_w
            ):
                mejor_1 = l1
                mejor_2 = l2

        if mejor_1:
            return mejor_1, mejor_2

        # Si no cabe ni así, dejar una sola línea y el método de centrado
        # reducirá automáticamente el tamaño.
        return texto, ""

    # ========================================================
    # FONDO
    # ========================================================

    @staticmethod
    def _dibujar_imagen_fondo(c, dx=0, dy=0):
        """
        Dibuja Credencial.png sin deformarla.

        Se utiliza ImageOps.fit() para adaptar cualquier PNG a la relación
        107:135 mediante recorte centrado, no mediante estiramiento.
        """
        ruta = EscarapelaPDFService._ruta_credencial()

        if not ruta.exists():
            c.setFillColor(HexColor("#FFF8E7"))
            c.rect(
                dx,
                dy,
                EscarapelaPDFService.W,
                EscarapelaPDFService.H,
                fill=1,
                stroke=0,
            )
            return

        try:
            with Image.open(ruta) as img:
                img = img.convert("RGBA")

                # Resolución suficiente para impresión.
                # La relación 107:135 se conserva exactamente.
                target_w = 2140
                target_h = 2700

                img = ImageOps.fit(
                    img,
                    (target_w, target_h),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )

                memoria = io.BytesIO()
                img.save(memoria, format="PNG", optimize=True)
                memoria.seek(0)

                c.drawImage(
                    ImageReader(memoria),
                    dx,
                    dy,
                    width=EscarapelaPDFService.W,
                    height=EscarapelaPDFService.H,
                    mask="auto",
                    preserveAspectRatio=False,
                )

        except Exception:
            c.setFillColor(HexColor("#FFF8E7"))
            c.rect(
                dx,
                dy,
                EscarapelaPDFService.W,
                EscarapelaPDFService.H,
                fill=1,
                stroke=0,
            )

    # ========================================================
    # COLORES POR ROL
    # ========================================================

    @staticmethod
    def _color_borde_rol(rol):
        return BADGE_ROL.get(rol, BADGE_ROL["APRENDIZ"])[0]

    # ========================================================
    # BADGE ROL
    # ========================================================

    @staticmethod
    def _badge_rol(c, rol, dx=0, dy=0):
        p = POS_BADGE

        color_fondo, color_texto = BADGE_ROL.get(
            rol,
            BADGE_ROL["APRENDIZ"],
        )

        texto = BADGE_ROL_TEXTO.get(
            rol,
            (rol or "").upper(),
        )

        x = dx + p["x"]
        y = dy + p["y"]
        w = p["w"]
        h = p["h"]

        c.setFillColor(color_fondo)
        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=0,
        )

        EscarapelaPDFService._centrar_en_caja(
            c=c,
            texto=texto,
            caja_x=x,
            caja_w=w,
            y=y + 2.45 * mm,
            fuente="Helvetica-Bold",
            tam=p["size"],
            color=color_texto,
            max_w=w - 6 * mm,
        )

    # ========================================================
    # NOMBRE + INSTITUCIÓN
    # ========================================================

    @staticmethod
    def _caja_nombre_contenido(c, persona, info, rol, dx=0, dy=0):
        p = POS_CAJA_NOMBRE
        borde = EscarapelaPDFService._color_borde_rol(rol)

        x = dx + p["x"]
        y = dy + p["y"]
        w = p["w"]
        h = p["h"]

        c.setFillColor(white)
        c.setStrokeColor(borde)
        c.setLineWidth(p["borde_grosor"])

        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=1,
        )

        max_w = w - 2 * p["padding_lados"]

        nombre = (persona.nombre_completo or "").upper()

        EscarapelaPDFService._centrar_en_caja(
            c=c,
            texto=nombre,
            caja_x=x,
            caja_w=w,
            y=dy + p["y_nombre"],
            fuente="Helvetica-Bold",
            tam=p["size_nombre"],
            color=black,
            max_w=max_w,
            tam_min=9,
        )

        institucion = ""

        if info["institucion"]:
            # No anteponer "I.E." porque la base ya debe contener
            # el nombre institucional normalizado.
            institucion = str(info["institucion"]).upper()

        elif info["programa"]:
            institucion = str(info["programa"]).upper()

        elif info["extra"]:
            institucion = str(info["extra"]).upper()

        if institucion:
            EscarapelaPDFService._centrar_en_caja(
                c=c,
                texto=institucion,
                caja_x=x,
                caja_w=w,
                y=dy + p["y_institucion"],
                fuente="Helvetica",
                tam=p["size_institucion"],
                color=GRIS_OSCURO,
                max_w=max_w,
                tam_min=6,
            )

    # ========================================================
    # DOCUMENTO
    # ========================================================

    @staticmethod
    def _caja_documento_contenido(c, info, rol, dx=0, dy=0):
        p = POS_CAJA_DOC
        borde = EscarapelaPDFService._color_borde_rol(rol)

        x = dx + p["x"]
        y = dy + p["y"]
        w = p["w"]
        h = p["h"]

        c.setFillColor(white)
        c.setStrokeColor(borde)
        c.setLineWidth(p["borde_grosor"])

        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=1,
        )

        tipo = (info["tipo_identificacion"] or "CC").upper()
        numero = str(info["numero_identificacion"] or "")

        texto = f"{tipo}: {numero}".strip()

        EscarapelaPDFService._centrar_en_caja(
            c=c,
            texto=texto,
            caja_x=x,
            caja_w=w,
            y=dy + p["y_texto"],
            fuente="Helvetica-Bold",
            tam=p["size"],
            color=COLOR_SENA_VERDE_OSCURO,
            max_w=w - 7 * mm,
            tam_min=7,
        )

    # ========================================================
    # PROYECTO + QR
    # ========================================================

    @staticmethod
    def _caja_inferior_proyecto_y_qr(
        c,
        persona,
        info,
        rol,
        dx=0,
        dy=0,
    ):
        p = POS_CAJA_INFERIOR
        borde = EscarapelaPDFService._color_borde_rol(rol)

        x = dx + p["x"]
        y = dy + p["y"]
        w = p["w"]
        h = p["h"]

        # Caja blanca simple.
        # Se elimina el marco verde exterior grueso.
        c.setFillColor(white)
        c.setStrokeColor(borde)
        c.setLineWidth(p["borde_grosor"])

        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=1,
        )

        # ----------------------------------------------------
        # TEXTO DEL PROYECTO
        # ----------------------------------------------------
        codigo = str(info["codigo_proyecto"] or "").strip()
        proyecto = str(info["proyecto"] or "").strip()

        if codigo and proyecto:
            linea1 = f"Proyecto: {codigo}"
            linea2 = proyecto

        elif proyecto:
            linea1 = "Proyecto:"
            linea2 = proyecto

        elif info["codigo_ficha"] and info["programa"]:
            linea1 = f"Ficha: {info['codigo_ficha']}"
            linea2 = str(info["programa"])

        elif info["programa"]:
            linea1 = "Programa:"
            linea2 = str(info["programa"])

        elif info["extra"]:
            linea1 = str(info["extra"])
            linea2 = ""

        else:
            linea1 = ""
            linea2 = ""

        max_w = w - 10 * mm

        if linea1:
            EscarapelaPDFService._centrar_en_caja(
                c=c,
                texto=linea1,
                caja_x=x,
                caja_w=w,
                y=dy + p["y_proyecto_1"],
                fuente="Helvetica-Bold",
                tam=p["size_label"],
                color=black,
                max_w=max_w,
                tam_min=6,
            )

        if linea2:
            l2a, l2b = EscarapelaPDFService._partir_texto_dos_lineas(
                c,
                linea2.upper(),
                "Helvetica-Bold",
                p["size_valor"],
                max_w,
            )

            if l2b:
                # Si realmente necesita dos líneas, se sube un poco
                # la primera para no invadir el QR.
                EscarapelaPDFService._centrar_en_caja(
                    c=c,
                    texto=l2a,
                    caja_x=x,
                    caja_w=w,
                    y=dy + 47.2 * mm,
                    fuente="Helvetica-Bold",
                    tam=7.6,
                    color=black,
                    max_w=max_w,
                    tam_min=6,
                )

                EscarapelaPDFService._centrar_en_caja(
                    c=c,
                    texto=l2b,
                    caja_x=x,
                    caja_w=w,
                    y=dy + 43.7 * mm,
                    fuente="Helvetica-Bold",
                    tam=7.6,
                    color=black,
                    max_w=max_w,
                    tam_min=6,
                )
            else:
                EscarapelaPDFService._centrar_en_caja(
                    c=c,
                    texto=l2a,
                    caja_x=x,
                    caja_w=w,
                    y=dy + p["y_proyecto_2"],
                    fuente="Helvetica-Bold",
                    tam=p["size_valor"],
                    color=black,
                    max_w=max_w,
                    tam_min=6,
                )

        # ----------------------------------------------------
        # QR
        # ----------------------------------------------------
        qr_size = p["qr_size"]

        qr_x = (
            dx
            + p["qr_centro_x"]
            - qr_size / 2
        )

        qr_y = dy + p["qr_y_inf"]

        ruta_qr = QrService.asegurarse_qr_existe(persona)

        try:
            c.drawImage(
                str(ruta_qr),
                qr_x,
                qr_y,
                width=qr_size,
                height=qr_size,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception:
            pass

    # ========================================================
    # FRENTE
    # ========================================================

    @staticmethod
    def _dibujar_frente(c, persona, evento, dx=0, dy=0):
        info = EscarapelaPDFService._info_persona(persona)
        rol = persona.tipo_persona

        # Orden de capas
        EscarapelaPDFService._dibujar_imagen_fondo(c, dx, dy)

        EscarapelaPDFService._badge_rol(
            c,
            rol,
            dx,
            dy,
        )

        EscarapelaPDFService._caja_nombre_contenido(
            c,
            persona,
            info,
            rol,
            dx,
            dy,
        )

        EscarapelaPDFService._caja_documento_contenido(
            c,
            info,
            rol,
            dx,
            dy,
        )

        EscarapelaPDFService._caja_inferior_proyecto_y_qr(
            c,
            persona,
            info,
            rol,
            dx,
            dy,
        )

    # ========================================================
    # INDIVIDUAL
    # ========================================================

    @staticmethod
    def _renderizar_persona(c, persona, evento, dx=0, dy=0):
        EscarapelaPDFService._dibujar_frente(
            c,
            persona,
            evento,
            dx,
            dy,
        )
        c.showPage()

    @staticmethod
    def generar_individual(persona, evento):
        buffer = io.BytesIO()

        c = canvas.Canvas(
            buffer,
            pagesize=(
                EscarapelaPDFService.W,
                EscarapelaPDFService.H,
            ),
        )

        EscarapelaPDFService._renderizar_persona(
            c,
            persona,
            evento,
        )

        c.save()
        buffer.seek(0)

        return buffer

    # ========================================================
    # HOJA CARTA 4 ESCARAPELAS
    # ========================================================

    @staticmethod
    def _slots_carta():
        """
        Orden:
        arriba izquierda
        arriba derecha
        abajo izquierda
        abajo derecha
        """
        slots = []

        total_w = 2 * EscarapelaPDFService.W + GUTTER
        total_h = 2 * EscarapelaPDFService.H + GUTTER

        margen_x = (CARTA_W - total_w) / 2
        margen_y = (CARTA_H - total_h) / 2

        for fila in (1, 0):
            for col in (0, 1):
                dx = margen_x + col * (
                    EscarapelaPDFService.W + GUTTER
                )

                dy = margen_y + fila * (
                    EscarapelaPDFService.H + GUTTER
                )

                slots.append((dx, dy))

        return slots

    @staticmethod
    def _bloques_carta(c, personas, evento, fn):
        slots = EscarapelaPDFService._slots_carta()

        for i in range(0, len(personas), 4):
            grupo = personas[i:i + 4]

            for idx, persona in enumerate(grupo):
                dx, dy = slots[idx]

                c.saveState()

                fn(
                    c,
                    persona,
                    evento,
                    dx,
                    dy,
                )

                c.restoreState()

            c.showPage()

    # ========================================================
    # GENERACIÓN POR LOTE
    # ========================================================

    @staticmethod
    def generar_lote(
        qs_personas,
        evento,
        titulo_lote=None,
        formato="CARTA_4X",
    ):
        personas = list(qs_personas)
        buffer = io.BytesIO()

        if formato == "INDIVIDUAL":
            c = canvas.Canvas(
                buffer,
                pagesize=(
                    EscarapelaPDFService.W,
                    EscarapelaPDFService.H,
                ),
            )

            for persona in personas:
                EscarapelaPDFService._renderizar_persona(
                    c,
                    persona,
                    evento,
                )

        else:
            c = canvas.Canvas(
                buffer,
                pagesize=letter,
            )

            EscarapelaPDFService._bloques_carta(
                c,
                personas,
                evento,
                EscarapelaPDFService._dibujar_frente,
            )

        c.save()
        buffer.seek(0)

        return buffer

    # ========================================================
    # FILTROS
    # ========================================================

    @staticmethod
    def generar_por_proyecto(
        proyecto,
        formato="CARTA_4X",
    ):
        from apps.personas.models import Persona

        evento = proyecto.evento

        qs = (
            Persona.objects
            .filter(
                perfil_aprendiz__proyecto=proyecto,
                activo=True,
            )
            .order_by(
                "apellidos",
                "nombres",
            )
        )

        return EscarapelaPDFService.generar_lote(
            qs,
            evento,
            f"Proyecto {proyecto.codigo}",
            formato=formato,
        )

    @staticmethod
    def generar_por_institucion(
        ie,
        evento,
        formato="CARTA_4X",
    ):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto

        ids = list(
            Proyecto.objects
            .filter(
                institucion=ie,
                evento=evento,
            )
            .values_list(
                "id",
                flat=True,
            )
        )

        qs = (
            Persona.objects
            .filter(
                perfil_aprendiz__proyecto_id__in=ids,
                activo=True,
            )
            .order_by(
                "apellidos",
                "nombres",
            )
        )

        return EscarapelaPDFService.generar_lote(
            qs,
            evento,
            f"IE {ie.codigo}",
            formato=formato,
        )

    @staticmethod
    def generar_por_programa(
        programa,
        evento,
        formato="CARTA_4X",
    ):
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto

        ids = list(
            Proyecto.objects
            .filter(
                programa=programa,
                evento=evento,
            )
            .values_list(
                "id",
                flat=True,
            )
        )

        q1 = Persona.objects.filter(
            perfil_aprendiz__proyecto_id__in=ids,
            activo=True,
        )

        q2 = Persona.objects.filter(
            perfil_instructor__programas=programa,
            activo=True,
        )

        qs = (
            (q1 | q2)
            .distinct()
            .order_by(
                "apellidos",
                "nombres",
            )
        )

        return EscarapelaPDFService.generar_lote(
            qs,
            evento,
            f"PR {programa.codigo}",
            formato=formato,
        )

    @staticmethod
    def generar_completo(
        evento,
        formato="CARTA_4X",
    ):
        from django.db.models import Q
        from apps.personas.models import Persona
        from apps.proyectos.models import Proyecto

        proyectos = list(
            Proyecto.objects
            .filter(evento=evento)
            .values_list(
                "id",
                flat=True,
            )
        )

        instructores = list(
            Proyecto.objects
            .filter(evento=evento)
            .exclude(
                instructor_responsable__isnull=True
            )
            .values_list(
                "instructor_responsable__persona_id",
                flat=True,
            )
        )

        qs = (
            Persona.objects
            .filter(activo=True)
            .filter(
                Q(
                    perfil_aprendiz__proyecto_id__in=proyectos
                )
                | Q(id__in=instructores)
                | Q(
                    tipo_persona__in=[
                        "INVITADO",
                        "ORGANIZADOR",
                    ]
                )
            )
            .distinct()
            .order_by(
                "tipo_persona",
                "apellidos",
                "nombres",
            )
        )

        return EscarapelaPDFService.generar_lote(
            qs,
            evento,
            "Completo",
            formato=formato,
        )
