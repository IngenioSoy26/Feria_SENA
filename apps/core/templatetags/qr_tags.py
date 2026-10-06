from django import template
from django.conf import settings
from pathlib import Path

from apps.core.utils import generar_qr_png

register = template.Library()


def _ruta_media_existe(ruta_relativa):
    if not ruta_relativa:
        return False
    try:
        if ruta_relativa.startswith(settings.MEDIA_URL):
            relativa = ruta_relativa[len(settings.MEDIA_URL):]
            return (Path(settings.MEDIA_ROOT) / relativa).exists()
        return False
    except Exception:
        return False


@register.simple_tag
def qr_image_url(persona, size=200):
    if persona is None:
        return ''
    atributo_ruta = getattr(persona, 'qr_ruta', None)
    if atributo_ruta and _ruta_media_existe(atributo_ruta):
        return atributo_ruta

    try:
        ruta = generar_qr_png(persona, size=size)
        if hasattr(persona, 'qr_ruta'):
            try:
                persona.qr_ruta = ruta
                persona.save(update_fields=['qr_ruta'])
            except Exception:
                pass
        return ruta
    except Exception:
        return ''
