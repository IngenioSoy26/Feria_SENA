from django.contrib import admin

admin.site.site_header = 'SENA - Administración Feria Proyectos'
admin.site.site_title = 'SENA Feria | Panel Admin'
admin.site.index_title = 'Panel de Gestión — Feria de Proyectos Productivos'
admin.site.enable_nav_sidebar = True

admin.site.site_url = '/dashboard/'

try:
    admin.AdminSite.site_header = 'SENA - Administración Feria Proyectos'
    admin.site._registry = admin.site._registry
except Exception:
    pass

from . import admin_panel_ops  # noqa: E402  (registra AsistenciaEventoAdmin + EntregaServicioAdmin)
