from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'
    verbose_name = 'Usuarios y Autenticación'

    def ready(self):
        # RESCATE INVERSO V38.2 (después de revertir V39):
        #   En V39.x habíamos DROPEADO columnas legacy 'nombres' y 'apellidos'
        #   de la tabla usuarios_usuario (porque eran @property). Ahora al
        #   volver a V38 el modelo Usuario los necesita NUEVAMENTE como
        #   CharField → los recreamos idempotentemente y populamos desde
        #   first_name / last_name. + drop residual unique email si quedó.
        try:
            from ._rescate_sql_vuelta_v38 import SQL_EJECUTAR_RESCATES_V38
            SQL_EJECUTAR_RESCATES_V38()
        except Exception:
            pass
