from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auditoria'
    verbose_name = 'Auditoría y Registro'

    def ready(self):
        from apps.auditoria import signals  # noqa: F401
        signals.conectar_signals_auditoria()
