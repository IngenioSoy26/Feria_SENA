from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


ROLES_SISTEMA = {
    'ADMINISTRADOR': ['todos'],
    'REGISTRO': [
        'view_evento', 'add_evento', 'change_evento',
        'view_institucioneducativa', 'add_institucioneducativa', 'change_institucioneducativa',
        'view_programatecnico', 'add_programatecnico', 'change_programatecnico',
        'view_instructor', 'add_instructor', 'change_instructor',
        'view_proyecto', 'add_proyecto', 'change_proyecto', 'delete_proyecto',
        'view_persona', 'add_persona', 'change_persona', 'delete_persona',
        'view_aprendiz', 'add_aprendiz', 'change_aprendiz', 'delete_aprendiz',
        'view_invitado', 'add_invitado', 'change_invitado', 'delete_invitado',
        'view_tiposervicio',
        'view_asistenciaevento', 'change_asistenciaevento',
        'view_entregaservicio',
        'view_certificado',
        'view_usuario',
    ],
    'GERENTE': [
        'view_evento',
        'view_institucioneducativa',
        'view_programatecnico',
        'view_instructor',
        'view_proyecto',
        'view_persona',
        'view_aprendiz',
        'view_invitado',
        'view_asistenciaevento',
        'view_entregaservicio',
        'view_tiposervicio',
        'view_certificado',
        'view_usuario',
    ],
    'OPERADOR_ASISTENCIA': [
        'view_evento',
        'view_institucioneducativa',
        'view_programatecnico',
        'view_instructor',
        'view_proyecto',
        'view_persona', 'change_persona',
        'view_invitado', 'change_invitado',
        'view_tiposervicio',
        'view_asistenciaevento', 'add_asistenciaevento', 'change_asistenciaevento', 'delete_asistenciaevento',
        'view_entregaservicio',
        'view_certificado', 'change_certificado',
    ],
    'OPERADOR_REFRIGERIO': [
        'view_evento',
        'view_institucioneducativa',
        'view_programatecnico',
        'view_instructor',
        'view_persona',
        'view_invitado',
        'view_asistenciaevento',
        'view_tiposervicio',
        'view_entregaservicio', 'add_entregaservicio', 'change_entregaservicio', 'delete_entregaservicio',
    ],
    'OPERADOR_CERTIFICADO': [
        'view_evento',
        'view_institucioneducativa',
        'view_programatecnico',
        'view_instructor',
        'view_proyecto',
        'view_persona',
        'view_invitado',
        'view_asistenciaevento', 'change_asistenciaevento',
        'view_tiposervicio',
        'view_certificado', 'add_certificado', 'change_certificado', 'delete_certificado',
    ],
    'CONSULTA': [
        'view_evento',
        'view_institucioneducativa',
        'view_programatecnico',
        'view_instructor',
        'view_proyecto',
        'view_persona',
        'view_aprendiz',
        'view_invitado',
        'view_asistenciaevento',
        'view_entregaservicio',
        'view_tiposervicio',
        'view_certificado',
        'view_usuario',
    ],
}


class Command(BaseCommand):
    help = 'Crea o actualiza los 6 roles de sistema (Groups) y asigna permisos según la matriz FASE0.'

    def _asignar_permisos_por_codename(self, grupo, codenames):
        encontrados = Permission.objects.filter(codename__in=codenames)
        encontrados_codes = set(encontrados.values_list('codename', flat=True))
        faltantes = [c for c in codenames if c not in encontrados_codes]
        for codename in faltantes:
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Permiso no encontrado en BD: {codename}')
            )
        grupo.permissions.add(*encontrados)
        return encontrados.count(), len(faltantes)

    def handle(self, *args, **options):
        self.stdout.write('=============================================')
        self.stdout.write('INICIALIZANDO ROLES DE SISTEMA SENA FERIA 2026')
        self.stdout.write('=============================================')

        total_permisos_ok = 0
        total_permisos_faltantes = 0

        for nombre_rol, permisos_rol in ROLES_SISTEMA.items():
            grupo, creado = Group.objects.get_or_create(name=nombre_rol)
            grupo.permissions.clear()

            accion = 'CREADO' if creado else 'ACTUALIZADO'
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(f'[{accion}] Grupo: {nombre_rol}'))

            if 'todos' in permisos_rol:
                todos = Permission.objects.all()
                grupo.permissions.add(*todos)
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Asignados TODOS los permisos ({todos.count()})')
                )
                total_permisos_ok += todos.count()
            else:
                ok, faltan = self._asignar_permisos_por_codename(grupo, permisos_rol)
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Asignados: {ok}  |  Faltantes en BD: {faltan}')
                )
                total_permisos_ok += ok
                total_permisos_faltantes += faltan

        self.stdout.write('')
        self.stdout.write('=============================================')
        self.stdout.write(self.style.SUCCESS(
            f'RESULTADO: {len(ROLES_SISTEMA)} roles procesados | '
            f'{total_permisos_ok} permisos asignados | '
            f'{total_permisos_faltantes} permisos no disponibles'
        ))
        self.stdout.write(self.style.WARNING(
            'Ejecute "python manage.py migrate" antes si faltan permisos de modelos nuevos.'
        ))
        self.stdout.write('=============================================')
