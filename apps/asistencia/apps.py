from django.apps import AppConfig


class AsistenciaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.asistencia'
    verbose_name = 'ASISTENCIA'

    def ready(self):
        try:
            from apps.core.admin_panel_ops import AsistenciaEventoAdmin  # noqa: F401
        except Exception:
            pass

