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
    "x": 19 * mm,
    "y": 72.5 * mm,
    "w": 69 * mm,
    "h": 8.5 * mm,
    "r": 4.25 * mm,
    "size": 12.5,
}


POS_CAJA_NOMBRE = {
    "x": 7 * mm,
    "y": 56.5 * mm,
    "w": 93 * mm,
    "h": 12.5 * mm,
    "r": 6 * mm,
    "borde_grosor": 0,
    "padding_lados": 5 * mm,
    "fill_alpha": 0.40,

    # Caja reducida: rango [56.5 → 69.0], centro geométrico = 62.75mm
    # IE en 59.5mm (gap 3.0mm sobre borde inferior → MUY CERCA como pides)
    # Nombre en 65.0mm, gap Nombre-IE 5.5mm (juntos)
    # Centro baselines: (65.0 + 59.5)/2 = 62.25mm  → 0.5mm vs centro geométrico 62.75 ✔ CENTRADO
    "y_nombre": 65.0 * mm,
    "y_institucion": 59.5 * mm,

    "size_nombre": 14,
    "size_institucion": 8.2,
}


POS_CAJA_DOC = {
    "x": 26 * mm,
    "y": 48.5 * mm,
    "w": 55 * mm,
    "h": 7.5 * mm,
    "r": 3.75 * mm,
    "borde_grosor": 0,
    "fill_alpha": 0.40,
    "y_texto": 51.1 * mm,
    "size": 11.5,
}


POS_CAJA_INFERIOR = {
    "x": 15.5 * mm,
    "y": 8.5 * mm,
    "w": 76 * mm,
    "h": 38.0 * mm,
    "r": 6 * mm,
    "borde_grosor": 0,

    # ✅ Fondo TRANSPARENTE (tal como lo solicitó el usuario).
    # Blanco con 40% opacidad: deja ver el arte del fondo Credencial.png
    # sin mezclar texto (ya NO pintamos nombre-proyecto → N/A).
    "fill_alpha": 0.40,

    # KEYS RETENIDAS (compatibilidad) — NUNCA se usan porque ahora la
    # caja inferior es SOLO QR para TODOS los roles (incluido APRENDIZ).
    "y_valor_solo": 13.5 * mm,
    "size_valor_solo": 9.2,
    "y_proyecto_1": 13.2 * mm,
    "size_label": 8.8,
    "y_proyecto_2": 11.9 * mm,
    "size_valor": 8.6,

    # QR 32mm (+14% vs v17 28mm) — CENTRADO, ocupa toda la zona.
    # qr_inf=14.5, qr_sup = 14.5 + 32 = 46.5 ≡ borde sup caja.
    "qr_size": 32 * mm,
    "qr_centro_x": 53.5 * mm,
    "qr_y_inf": 14.5 * mm,
}


# =========================================================================
# CACHE GLOBAL DE LA IMAGEN DE FONDO PROCESADA CON ImageOps.pad().
#
# SIN ESTO: ImageOps.pad LANCZOS 2140×2700 + save PNG + io.BytesIO()
#          por cada tarjeta. 300 personas = 30s → Railway timeout.
#
# CON ESTO: 1 SOLA VEZ por proceso Railway. Render lote 300 = ~1 segundo.
#
# Invalidación cache: st_mtime_ns Credencial.png cambia (actualizas plantilla)
# → cache regenera sola en el siguiente request.
# =========================================================================
_FONDO_CREDENCIAL_BYTESIO = None          # BytesIO PNG ya pad-2140×2700
_FONDO_CREDENCIAL_MTIME = None            # mtime Credencial.png
_FONDO_CREDENCIAL_RUTA_STR = None         # ruta que generó la cache


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
                abrev = (getattr(persona.tipo_identificacion, "abreviatura", None) or "").strip().upper()
                if abrev:
                    info["tipo_identificacion"] = abrev
                else:
                    codigo = (getattr(persona.tipo_identificacion, "codigo", None) or "").strip().upper()
                    info["tipo_identificacion"] = codigo or ""
        except Exception:
            pass

        info["numero_identificacion"] = persona.numero_identificacion or ""

        # Campos de Persona raíz (ahora contienen entidad/cargo para TODOS los roles)
        # Prioridad: entidad y cargo de Persona (nuevos campos), fallback al perfil específico
        # === PROTECCIÓN v29: columnas Persona.entidad / Persona.cargo / Instructor.entidad NO migradas aún ===
        _p_ent = ""
        _p_car = ""
        try:
            from django.db.utils import ProgrammingError as _PE_SVC
        except Exception:
            _PE_SVC = Exception
        try:
            _p_ent = (getattr(persona, "entidad", None) or "").strip()
        except (_PE_SVC, AttributeError, Exception):
            try:
                from django.db import connection as _conn_svc
                try: _conn_svc.rollback()
                except Exception: pass
                try: _conn_svc.close()
                except Exception: pass
            except Exception:
                pass
            _p_ent = ""
        try:
            _p_car = (getattr(persona, "cargo", None) or "").strip()
        except (_PE_SVC, AttributeError, Exception):
            try:
                from django.db import connection as _conn_svc2
                try: _conn_svc2.rollback()
                except Exception: pass
                try: _conn_svc2.close()
                except Exception: pass
            except Exception:
                pass
            _p_car = ""

        def _safe_attr(obj, attr, default=""):
            try:
                v = getattr(obj, attr, default)
                return (v or "").strip() if not isinstance(v, (int, float)) else (v or default)
            except Exception:
                try:
                    from django.db import connection as _conn_safe
                    try: _conn_safe.rollback()
                    except Exception: pass
                    try: _conn_safe.close()
                    except Exception: pass
                except Exception:
                    pass
                return default

        if persona.tipo_persona == "APRENDIZ":
            perfil = getattr(persona, "perfil_aprendiz", None)

            if perfil and perfil.proyecto:
                proyecto = perfil.proyecto

                info["proyecto"] = proyecto.nombre
                info["codigo_proyecto"] = getattr(proyecto, "codigo", None)

                if proyecto.institucion:
                    info["institucion"] = _p_ent or proyecto.institucion.nombre
                else:
                    info["institucion"] = _p_ent or info.get("institucion") or None

                if proyecto.programa:
                    info["programa"] = proyecto.programa.nombre

                if proyecto.ficha:
                    info["codigo_ficha"] = proyecto.ficha.numero
            else:
                if _p_ent:
                    info["institucion"] = _p_ent

            if _p_car:
                info["extra"] = _p_car
            else:
                info["extra"] = info.get("extra") or "APRENDIZ"

        elif persona.tipo_persona == "INSTRUCTOR":
            perfil = getattr(persona, "perfil_instructor", None)

            if perfil:
                programas = list(perfil.programas.all()[:2])

                if programas:
                    info["programa"] = " · ".join(
                        p.nombre for p in programas
                    )

            info["institucion"] = _p_ent or (_safe_attr(perfil, "entidad") if perfil else "") or "SENA"
            info["extra"] = _p_car or (_safe_attr(perfil, "cargo") if perfil else "") or "INSTRUCTOR SENA"

        elif persona.tipo_persona == "INVITADO":
            perfil = getattr(persona, "perfil_invitado", None)

            if perfil:
                info["institucion"] = _p_ent or _safe_attr(perfil, "entidad") or info.get("institucion") or None
                info["extra"] = _p_car or _safe_attr(perfil, "cargo") or info.get("extra") or None
            else:
                info["institucion"] = _p_ent or info.get("institucion") or None
                info["extra"] = _p_car or info.get("extra") or None

        elif persona.tipo_persona == "ORGANIZADOR":
            perfil = getattr(persona, "perfil_organizador", None)
            info["institucion"] = _p_ent or (_safe_attr(perfil, "entidad") if perfil else "") or None
            info["extra"] = _p_car or (_safe_attr(perfil, "cargo") if perfil else "") or "ORGANIZADOR"

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
        Dibuja Credencial.png SIN CORTAR NADA 100% CONTENIDO VISIBLE.

        --- MOTIVO por el que se quitó ImageOps.fit() ---
        Credencial.png actual = 1024 ancho × 1536 alto (ratio 0.667).
        Escarapela física    = 107mm W × 135mm H  (ratio 0.793 MÁS ANCHA).
        ImageOps.fit() recortaba centrado → cortaba:
          - ARRIBA: el título "VI Feria / Proyectos Productivos / CENTRO..."
          - ABAJO: desierto / cactus / mar.
        Usuario: "la imagen del fondo quedo cortada".

        --- SOLUCIÓN: ImageOps.pad(color = beige SENA #FFF1D8) ---
        Resultado: CONTENIDO PNG 100% visible (sin cortar nada).
        El espacio "sobrante" a izquierda y derecha del PNG más estrecho
        se RELLENA con color beige idéntico al degradado de Credencial.png
        → visualmente INPERCEPTIBLE, como si la imagen ocupara todo el ancho.
        + Cache global singleton (1 vez proceso Railway, 0 Pillow por tarjeta).
        + Invalida cache cuando st_mtime_ns de Credencial.png cambia
          (subes nueva plantilla).
        + Fallback drawImage directo SIN Pillow = nunca pantalla negra.
        """
        global _FONDO_CREDENCIAL_BYTESIO, _FONDO_CREDENCIAL_MTIME, _FONDO_CREDENCIAL_RUTA_STR
        ruta = EscarapelaPDFService._ruta_credencial()

        if not ruta.exists():
            c.setFillColor(HexColor("#FFF8E7"))
            c.rect(
                dx, dy, EscarapelaPDFService.W, EscarapelaPDFService.H,
                fill=1, stroke=0,
            )
            return

        # --- Cache válida? ---
        usar_cache = False
        ruta_str = str(ruta)
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if (
            _FONDO_CREDENCIAL_BYTESIO is not None
            and _FONDO_CREDENCIAL_RUTA_STR == ruta_str
            and _FONDO_CREDENCIAL_MTIME == mtime
        ):
            usar_cache = True

        if usar_cache:
            try:
                _FONDO_CREDENCIAL_BYTESIO.seek(0)
                c.drawImage(
                    ImageReader(_FONDO_CREDENCIAL_BYTESIO),
                    dx, dy,
                    width=EscarapelaPDFService.W,
                    height=EscarapelaPDFService.H,
                    mask="auto",
                    preserveAspectRatio=False,
                )
                return
            except Exception:
                _FONDO_CREDENCIAL_BYTESIO = None
                _FONDO_CREDENCIAL_RUTA_STR = None
                _FONDO_CREDENCIAL_MTIME = None

        # --- Regenerar cache: PAD (no más FIT) = 0 cortes ---
        try:
            with Image.open(ruta) as img:
                img = img.convert("RGBA")
                target_w = 2140
                target_h = 2700
                # Beige degradado SENA extraído del borde de Credencial.png
                # Cualquier pixel del borde exterior tiene ese tono.
                color_padding = (255, 241, 216, 255)
                img = ImageOps.pad(
                    img,
                    (target_w, target_h),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                    color=color_padding,
                )
                memoria = io.BytesIO()
                img.save(memoria, format="PNG", optimize=True)
                memoria.seek(0)
            _FONDO_CREDENCIAL_BYTESIO = memoria
            _FONDO_CREDENCIAL_RUTA_STR = ruta_str
            _FONDO_CREDENCIAL_MTIME = mtime
            _FONDO_CREDENCIAL_BYTESIO.seek(0)
            c.drawImage(
                ImageReader(_FONDO_CREDENCIAL_BYTESIO),
                dx, dy,
                width=EscarapelaPDFService.W,
                height=EscarapelaPDFService.H,
                mask="auto",
                preserveAspectRatio=False,
            )
        except Exception:
            # Fallback definitivo: drawImage directo SIN Pillow
            try:
                c.drawImage(
                    ruta_str,
                    dx, dy,
                    width=EscarapelaPDFService.W,
                    height=EscarapelaPDFService.H,
                    mask="auto",
                    preserveAspectRatio=False,
                )
            except Exception:
                c.setFillColor(HexColor("#FFF8E7"))
                c.rect(
                    dx, dy, EscarapelaPDFService.W, EscarapelaPDFService.H,
                    fill=1, stroke=0,
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

        c.saveState()
        c.setFillColor(white)
        c.setFillAlpha(p["fill_alpha"])
        c.setStrokeColor(borde)
        c.setLineWidth(p["borde_grosor"])

        _stroke = 1 if p["borde_grosor"] > 0 else 0
        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=_stroke,
        )
        c.restoreState()

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

        c.saveState()
        c.setFillColor(white)
        c.setFillAlpha(p["fill_alpha"])
        c.setStrokeColor(borde)
        c.setLineWidth(p["borde_grosor"])

        _stroke = 1 if p["borde_grosor"] > 0 else 0
        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=_stroke,
        )
        c.restoreState()

        tipo = (info["tipo_identificacion"] or "").strip().upper()
        numero = str(info["numero_identificacion"] or "")

        if tipo and numero:
            texto = "{}: {}".format(tipo, numero)
        else:
            texto = (numero or tipo).strip()
        texto = texto.strip()

        EscarapelaPDFService._centrar_en_caja(
            c=c,
            texto=texto,
            caja_x=x,
            caja_w=w,
            y=dy + p["y_texto"],
            fuente="Helvetica-Bold",
            tam=p["size"],
            color=black,
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

        # Caja blanca con transparencia (solo el fondo, no el borde)
        c.saveState()
        c.setFillColor(white)
        c.setFillAlpha(p["fill_alpha"])
        c.setStrokeColor(borde)
        c.setLineWidth(p["borde_grosor"])

        _stroke = 1 if p["borde_grosor"] > 0 else 0
        c.roundRect(
            x,
            y,
            w,
            h,
            p["r"],
            fill=1,
            stroke=_stroke,
        )
        c.restoreState()

        # ----------------------------------------------------
        # ✅ SIN TEXTO DE PROYECTO (orden explícita del usuario).
        # CAJA INFERIOR = SOLO QR 32mm PARA TODOS LOS ROLES
        # (APRENDIZ / INSTRUCTOR / INVITADO / ORGANIZADOR).
        # El nombre del proyecto NUNCA se muestra en la credencial.
        # ----------------------------------------------------
        pass

        # ----------------------------------------------------
        # QR (achicado 26mm + semi-transparente alpha)
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
            # --- Semi-transparencia QR: efecto "no 100% opaco" ---
            # Técnica ReportLab: saveState → setFillAlpha(0.82) en un
            # recuadro BLANCO padding detrás + drawImage normal.
            # El ojo percibe "menos brusco/transparente".
            c.saveState()
            c.setFillColor(white)
            c.setFillAlpha(0.82)
            # Padding 1.2mm alrededor del QR para "glow" translúcido.
            c.rect(
                qr_x - 1.2 * mm,
                qr_y - 1.2 * mm,
                qr_size + 2.4 * mm,
                qr_size + 2.4 * mm,
                fill=1,
                stroke=0,
            )
            c.restoreState()

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
