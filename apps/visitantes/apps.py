from django.apps import AppConfig


class VisitantesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.visitantes'
    verbose_name = 'Visitantes'
    label = 'visitantes'

    def ready(self):
        try:
            from django.contrib import admin
            from . import models as _m
            from . import admin as _admin_mod
        except Exception:
            pass
