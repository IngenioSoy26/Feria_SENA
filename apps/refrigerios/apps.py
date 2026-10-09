from django.apps import AppConfig


class RefrigeriosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.refrigerios'
    verbose_name = 'REFRIGERIOS'

    def ready(self):
        try:
            from apps.core.admin_panel_ops import EntregaServicioAdmin  # noqa: F401
        except Exception:
            pass

