import json
import logging

logger = logging.getLogger(__name__)


class AuditoriaService:
    @staticmethod
    def _obtener_ip(request):
        if not request:
            return None
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def _obtener_user_agent(request):
        if not request:
            return None
        ua = request.META.get('HTTP_USER_AGENT', '')
        return ua[:255] if ua else None

    @staticmethod
    def _construir_datos(accion=None, modulo=None, entidad=None, id_entidad=None, datos=None):
        resultado = {}
        if accion:
            resultado['accion'] = accion
        if modulo:
            resultado['modulo'] = modulo
        if entidad:
            resultado['entidad'] = entidad
            if id_entidad is not None:
                resultado['id_entidad'] = id_entidad
        if datos is not None:
            if isinstance(datos, (dict, list)):
                resultado['payload'] = datos
            else:
                try:
                    resultado['payload'] = json.loads(json.dumps(datos, default=str, ensure_ascii=False))
                except Exception:
                    resultado['payload'] = str(datos)
        return resultado if resultado else None

    @staticmethod
    def registrar(
        request=None,
        usuario=None,
        accion=None,
        modulo=None,
        entidad=None,
        id_entidad=None,
        datos=None,
    ):
        try:
            from apps.auditoria.models import AuditLog

            usuario_obj = usuario
            if usuario_obj is None and request is not None:
                if getattr(request, 'user', None) and request.user.is_authenticated:
                    usuario_obj = request.user

            ip = AuditoriaService._obtener_ip(request)
            user_agent = AuditoriaService._obtener_user_agent(request)
            datos_json = AuditoriaService._construir_datos(
                accion=accion,
                modulo=modulo,
                entidad=entidad,
                id_entidad=id_entidad,
                datos=datos,
            )

            accion_final = 'GENERICA'
            if accion:
                accion_normalizada = str(accion).upper()
                acciones_validas = {a[0] for a in AuditLog.ACCIONES}
                if accion_normalizada in acciones_validas:
                    accion_final = accion_normalizada
                elif modulo:
                    modulo_norm = str(modulo).upper()
                    if modulo_norm in acciones_validas:
                        accion_final = modulo_norm

            modulo_str = str(modulo)[:50] if modulo else None
            entidad_str = str(entidad)[:100] if entidad else None
            id_entidad_int = None
            if id_entidad is not None:
                try:
                    id_entidad_int = int(id_entidad)
                except (ValueError, TypeError):
                    id_entidad_int = None

            AuditLog.objects.create(
                usuario=usuario_obj,
                accion=accion_final,
                modulo=modulo_str or '',
                entidad=entidad_str,
                id_entidad=id_entidad_int,
                datos=datos_json,
                ip=ip,
                user_agent=user_agent or '',
            )
        except Exception as e:
            logger.exception('Error registrando auditoria: %s', e)
