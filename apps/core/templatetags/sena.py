from django import template

register = template.Library()


@register.filter
def has_group(user, group_name):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.groups.filter(name=group_name).exists()


@register.filter
def badge_color_rol(rol):
    if not rol:
        return 'badge-secondary'
    rol_mayus = str(rol).upper()
    if rol_mayus == 'APRENDIZ':
        return 'badge-aprendiz'
    if rol_mayus == 'INSTRUCTOR':
        return 'badge-instructor'
    if rol_mayus == 'INVITADO':
        return 'badge-invitado'
    if rol_mayus == 'ORGANIZADOR':
        return 'badge-organizador'
    return 'badge-secondary'


@register.filter
def iniciales(nombre):
    if not nombre:
        return ''
    texto = str(nombre).strip()
    if not texto:
        return ''
    partes = [p for p in texto.split() if p]
    if not partes:
        return ''
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()
