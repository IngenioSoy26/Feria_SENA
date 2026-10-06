from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps


MODELOS_A_AUDITAR = [
    ('personas', 'Persona'),
    ('aprendices', 'Aprendiz'),
    ('instructores', 'Instructor'),
    ('invitados', 'Invitado'),
    ('proyectos', 'Proyecto'),
    ('instituciones', 'InstitucionEducativa'),
    ('programas', 'ProgramaTecnico'),
    ('eventos', 'Evento'),
    ('usuarios', 'Usuario'),
    ('refrigerios', 'TipoServicio'),
    ('asistencia', 'AsistenciaEvento'),
    ('refrigerios', 'EntregaServicio'),
    ('certificados', 'Certificado'),
]


def _obtener_modelos():
    modelos = []
    for app_label, model_name in MODELOS_A_AUDITAR:
        try:
            modelo = apps.get_model(app_label, model_name)
            modelos.append((modelo, app_label, model_name))
        except LookupError:
            continue
    return modelos


def _registrar_auditoria_signal(instance, accion, app_label, model_name, datos_extra=None):
    try:
        from apps.core.services import AuditoriaService

        id_entidad = getattr(instance, 'pk', None) or getattr(instance, 'id', None)
        representacion = ''
        try:
            representacion = str(instance)[:100]
        except Exception:
            representacion = model_name

        datos = {
            'model': model_name,
            'app': app_label,
            'str': representacion,
        }
        if datos_extra:
            datos.update(datos_extra)

        AuditoriaService.registrar(
            request=None,
            usuario=None,
            accion=accion,
            modulo=app_label.upper(),
            entidad=model_name,
            id_entidad=id_entidad,
            datos=datos,
        )
    except Exception:
        pass


def conectar_signals_auditoria():
    for modelo, app_label, model_name in _obtener_modelos():

        @receiver(post_save, sender=modelo, weak=False, dispatch_uid=f'post_save_{app_label}_{model_name}')
        def handler_post_save(sender, instance, created, **kwargs):
            accion_signal = 'CREATE' if created else 'UPDATE'
            _registrar_auditoria_signal(
                instance,
                accion_signal,
                sender._meta.app_label,
                sender._meta.object_name,
                datos_extra={'created': created},
            )

        @receiver(post_delete, sender=modelo, weak=False, dispatch_uid=f'post_delete_{app_label}_{model_name}')
        def handler_post_delete(sender, instance, **kwargs):
            _registrar_auditoria_signal(
                instance,
                'DELETE',
                sender._meta.app_label,
                sender._meta.object_name,
            )
