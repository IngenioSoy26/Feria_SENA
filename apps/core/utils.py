import uuid
from pathlib import Path

from django.conf import settings


def anonimizar_cedula(numero):
    if not numero:
        return ''
    texto = str(numero).strip()
    if len(texto) < 4:
        return '*' * len(texto)
    return f'{texto[:2]}***{texto[-2:]}'


def formato_fecha_hora_co(dt):
    if not dt:
        return ''
    try:
        return dt.strftime('%d/%m/%Y %I:%M %p')
    except (AttributeError, ValueError):
        return str(dt)


def _obtener_logo_sena():
    logo_path = Path(settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.BASE_DIR / 'static') / 'img' / 'logo-sena-verde.png'
    if logo_path.exists():
        try:
            from PIL import Image
            return Image.open(logo_path).convert('RGBA')
        except Exception:
            return None
    return None


def generar_qr_png(persona, size=300):
    import qrcode
    from PIL import Image

    media_root = Path(settings.MEDIA_ROOT)
    qr_dir = media_root / 'qr'
    qr_dir.mkdir(parents=True, exist_ok=True)

    nombre_archivo = f'{uuid.uuid4()}.png'
    ruta_salida = qr_dir / nombre_archivo

    contenido = ''
    if hasattr(persona, 'qr_token') and persona.qr_token:
        contenido = str(persona.qr_token)
    elif hasattr(persona, 'id'):
        contenido = f'persona:{getattr(persona, "numero_id", "") or persona.id}'
    else:
        contenido = str(persona)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(contenido)
    qr.make(fit=True)

    img_qr = qr.make_image(fill_color='#006633', back_color='white').convert('RGBA')
    img_qr = img_qr.resize((size, size), Image.LANCZOS)

    logo = _obtener_logo_sena()
    if logo is not None:
        tam_logo = max(size // 5, 48)
        logo = logo.resize((tam_logo, tam_logo), Image.LANCZOS)
        pos_x = (img_qr.size[0] - logo.size[0]) // 2
        pos_y = (img_qr.size[1] - logo.size[1]) // 2
        fondo_blanco = Image.new('RGBA', (tam_logo + 8, tam_logo + 8), 'white')
        fondo_blanco.paste(logo, (4, 4), logo)
        img_qr.paste(fondo_blanco, (pos_x - 4, pos_y - 4), fondo_blanco)

    img_qr.save(ruta_salida, format='PNG')

    return f'{settings.MEDIA_URL}qr/{nombre_archivo}'
