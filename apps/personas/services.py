from pathlib import Path

from django.conf import settings


class QrService:
    QR_COLOR_OSCURO = '#1a1a1a'
    QR_COLOR_FONDO = 'white'
    LOGO_SIZE_RATIO = 0.15
    LOGO_BORDE_PX = 6

    @staticmethod
    def _ruta_logo_sena():
        static_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / 'static']
        return Path(static_dirs[0]) / 'img' / 'logo-sena-verde.png'

    @staticmethod
    def _ruta_qr_dir():
        ruta = Path(settings.MEDIA_ROOT) / 'qr'
        ruta.mkdir(parents=True, exist_ok=True)
        return ruta

    @staticmethod
    def _ruta_qr_archivo(persona):
        return QrService._ruta_qr_dir() / f'{str(persona.qr_token)}.png'

    @staticmethod
    def generar_qr_png(persona, size=300):
        import qrcode
        from PIL import Image, ImageOps

        ruta_salida = QrService._ruta_qr_archivo(persona)

        contenido_qr = str(persona.qr_token)

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(contenido_qr)
        qr.make(fit=True)

        img_qr = qr.make_image(
            fill_color=QrService.QR_COLOR_OSCURO,
            back_color=QrService.QR_COLOR_FONDO,
        ).convert('RGBA')
        img_qr = img_qr.resize((size, size), Image.LANCZOS)

        ruta_logo = QrService._ruta_logo_sena()
        if ruta_logo.exists():
            try:
                logo = Image.open(ruta_logo).convert('RGBA')
                tam_logo = max(int(size * QrService.LOGO_SIZE_RATIO), 24)
                logo = logo.resize((tam_logo, tam_logo), Image.LANCZOS)

                tam_con_borde = tam_logo + QrService.LOGO_BORDE_PX * 2
                fondo_blanco = Image.new('RGBA', (tam_con_borde, tam_con_borde), 'white')

                pos_logo_en_fondo = (
                    (tam_con_borde - tam_logo) // 2,
                    (tam_con_borde - tam_logo) // 2,
                )
                fondo_blanco.paste(logo, pos_logo_en_fondo, logo)

                pos_final = (
                    (img_qr.size[0] - tam_con_borde) // 2,
                    (img_qr.size[1] - tam_con_borde) // 2,
                )
                img_qr.paste(fondo_blanco, pos_final, fondo_blanco)
            except Exception:
                pass

        img_qr.save(ruta_salida, format='PNG')

        return str(ruta_salida.resolve())

    @staticmethod
    def asegurarse_qr_existe(persona):
        ruta = QrService._ruta_qr_archivo(persona)
        if not ruta.exists():
            return QrService.generar_qr_png(persona)
        return str(ruta.resolve())
