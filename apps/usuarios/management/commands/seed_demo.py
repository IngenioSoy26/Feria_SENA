import random
from datetime import date

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import Group

from apps.usuarios.models import Usuario
from apps.eventos.models import TipoIdentificacion, Evento, TipoServicio
from apps.instituciones.models import InstitucionEducativa
from apps.programas.models import ProgramaTecnico
from apps.personas.models import Persona
from apps.instructores.models import Instructor
from apps.proyectos.models import Proyecto, Aprendiz
from apps.invitados.models import Invitado


PASSWORD_DEMO = 'DemoSena1234*'

NOMBRES_COLOMBIANOS = [
    'Juan', 'Carlos', 'Andrés', 'Felipe', 'Santiago', 'José', 'Miguel', 'David',
    'Daniel', 'Alejandro', 'Mateo', 'Nicolás', 'Simón', 'Sebastián', 'Luis',
    'María', 'Camila', 'Sofía', 'Valentina', 'Isabella', 'Laura', 'Daniela',
    'Ana', 'Carolina', 'Gabriela', 'Paula', 'Andrea', 'Manuela', 'Juliana',
    'Fernanda', 'Lorena', 'Catalina', 'Mariana', 'Natalia', 'Stephany',
    'Jorge', 'Pablo', 'Ricardo', 'Álvaro', 'Gustavo', 'Hernán', 'Diego',
    'Roberto', 'César', 'Diana', 'Mónica', 'Liliana', 'Claudia', 'Martha',
    'Nancy', 'Patricia', 'Alba', 'Luz', 'Gloria', 'Rosa', 'Viviana', 'Lina',
    'Yenny', 'Jessica', 'Jenny', 'Yesenia', 'Wilmer', 'Stiven', 'Brayan',
    'Jhon', 'Cristian', 'Kevin', 'Steven', 'Julián', 'Brandon', 'Miller',
]

APELLIDOS_COLOMBIANOS = [
    'García', 'Rodríguez', 'Martínez', 'López', 'González', 'Hernández',
    'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Rivera', 'Gómez',
    'Díaz', 'Reyes', 'Morales', 'Castillo', 'Ortiz', 'Álvarez', 'Ruiz',
    'Jiménez', 'Alonso', 'Romero', 'Núñez', 'Molina', 'Suárez', 'Durán',
    'Vargas', 'Castro', 'Guzmán', 'Salazar', 'Cárdenas', 'Rojas', 'Quintero',
    'Miranda', 'Vega', 'Cano', 'Méndez', 'Cruz', 'Gil', 'Parra', 'Ríos',
    'Contreras', 'Medina', 'Herrera', 'Rangel', 'Cortés', 'Sepúlveda',
    'Ibarra', 'Villalba', 'Pinto', 'Arrieta', 'Angulo', 'Perea', 'Benítez',
    'Acosta', 'Bolaños', 'Osorio', 'Palacios', 'Londoño', 'Mesa', 'Roa',
    'Zuluaga', 'Espinosa', 'Solano', 'Lozano', 'Márquez', 'Zapata',
]

INSTITUCIONES_DEMO = [
    {'codigo': 'INS-001', 'nombre': 'INSTITUCION EDUCATIVA SAN JUAN BAUTISTA', 'municipio': 'RIOHACHA'},
    {'codigo': 'INS-002', 'nombre': 'INSTITUCION EDUCATIVA TÉCNICA REMEDIOS SOLANO', 'municipio': 'BARRANCAS'},
    {'codigo': 'INS-003', 'nombre': 'INSTITUCION EDUCATIVA CENTRO DE INTEGRACION POPULAR', 'municipio': 'RIOHACHA'},
    {'codigo': 'INS-004', 'nombre': 'INSTITUCIÓN EDUCATIVA CHON-KAY', 'municipio': 'RIOHACHA'},
    {'codigo': 'INS-005', 'nombre': 'INSTITUCION EDUCATIVA NO. 6 - SEDE PRINCIPAL - JORGE ARRIETA', 'municipio': 'MAICAO'},
]

PROGRAMAS_DEMO = [
    {'codigo': 'PROG-001', 'nombre': 'ASIS ADMINISTRATIVA'},
    {'codigo': 'PROG-002', 'nombre': 'COCINA'},
    {'codigo': 'PROG-003', 'nombre': 'CONTABILIZACIÓN DE OCF'},
    {'codigo': 'PROG-004', 'nombre': 'MANTENIMIENTO DE EQUIPOS DE CÓMPUTO'},
    {'codigo': 'PROG-005', 'nombre': 'PROG DE SOFTWARE'},
]

ENTIDADES_INVITADOS = [
    ('Alcaldía Municipal de Riohacha', 'Alcalde'),
    ('Gobernación del Departamento de La Guajira', 'Gobernador'),
    ('Universidad de La Guajira', 'Rector'),
    ('SENA Regional Guajira', 'Director Regional'),
    ('Cámara de Comercio de Riohacha', 'Presidente'),
    ('Alcaldía Municipal de Maicao', 'Secretario de Educación'),
    ('Gobernación del Cesar', 'Secretario Técnico'),
    ('Universidad del Magdalena', 'Decano de Ingeniería'),
    ('UNAD - Universidad Nacional Abierta y a Distancia', 'Director Centro'),
    ('Corporación La Guajira Progresa', 'Director Ejecutivo'),
]

USUARIOS_DEMO = [
    {'username': 'admin_demo', 'rol': 'ADMINISTRADOR', 'email': 'admin_demo@senaferia.edu.co', 'nombres': 'Administrador', 'apellidos': 'Demo'},
    {'username': 'registro_demo', 'rol': 'REGISTRO', 'email': 'registro_demo@senaferia.edu.co', 'nombres': 'Usuario', 'apellidos': 'Registro'},
    {'username': 'asistencia_demo', 'rol': 'OPERADOR_ASISTENCIA', 'email': 'asistencia_demo@senaferia.edu.co', 'nombres': 'Operador', 'apellidos': 'Asistencia'},
    {'username': 'refrigerio_demo', 'rol': 'OPERADOR_REFRIGERIO', 'email': 'refrigerio_demo@senaferia.edu.co', 'nombres': 'Operador', 'apellidos': 'Refrigerio'},
    {'username': 'certificado_demo', 'rol': 'OPERADOR_CERTIFICADO', 'email': 'certificado_demo@senaferia.edu.co', 'nombres': 'Operador', 'apellidos': 'Certificado'},
    {'username': 'consulta_demo', 'rol': 'CONSULTA', 'email': 'consulta_demo@senaferia.edu.co', 'nombres': 'Usuario', 'apellidos': 'Consulta'},
]


class Command(BaseCommand):
    help = 'Carga completa de datos demo: roles, usuarios, eventos, instituciones, programas, instructores, proyectos, aprendices e invitados.'

    def _crear_usuarios_demo(self):
        for data in USUARIOS_DEMO:
            user, created = Usuario.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'nombres': data['nombres'],
                    'apellidos': data['apellidos'],
                    'rol_sistema': data['rol'],
                    'activo': True,
                }
            )
            user.set_password(PASSWORD_DEMO)
            user.rol_sistema = data['rol']
            user.save()

            try:
                grupo = Group.objects.get(name=data['rol'])
                user.groups.add(grupo)
            except Group.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠ Grupo {data["rol"]} no encontrado'))

            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Usuario creado: {data["username"]} → {data["rol"]}'))
            else:
                self.stdout.write(f'  ↻ Usuario actualizado: {data["username"]} → {data["rol"]}')

    def _crear_tipos_identificacion(self):
        tipos = [
            {'codigo': 'CC', 'nombre': 'Cédula de Ciudadanía'},
            {'codigo': 'TI', 'nombre': 'Tarjeta de Identidad'},
            {'codigo': 'PPT', 'nombre': 'Permiso por Protección Temporal'},
        ]
        for t in tipos:
            obj, created = TipoIdentificacion.objects.get_or_create(
                codigo=t['codigo'],
                defaults={'nombre': t['nombre'], 'activo': True},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ TipoIdentificacion: {t["codigo"]}'))

    def _crear_evento_demo(self):
        evento, created = Evento.objects.get_or_create(
            nombre='FERIA DEMO PROYECTOS PRODUCTIVOS 2026',
            defaults={
                'fecha_inicio': date(2026, 11, 20),
                'fecha_fin': date(2026, 11, 22),
                'lugar': 'Coliseo Cubierto Riohacha',
                'municipio': 'Riohacha',
                'regional': 'Guajira',
                'estado': 'ACTIVO',
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Evento creado: {evento.nombre}'))
        else:
            self.stdout.write(f'  ↻ Evento ya existe: {evento.nombre}')
        return evento

    def _crear_tipos_servicio(self, evento):
        servicios = [
            ('Refrigerio mañana', 1, False),
            ('Almuerzo', 2, True),
            ('Refrigerio tarde', 3, False),
        ]
        for nombre, orden, activo in servicios:
            obj, created = TipoServicio.objects.get_or_create(
                evento=evento,
                nombre=nombre,
                defaults={'orden': orden, 'activo': activo},
            )
            if obj.activo != activo:
                obj.activo = activo
                obj.save()
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ TipoServicio: {nombre} (activo={activo})'))

    def _crear_instituciones(self):
        creadas = []
        for data in INSTITUCIONES_DEMO:
            obj, created = InstitucionEducativa.objects.get_or_create(
                codigo=data['codigo'],
                defaults={'nombre': data['nombre'], 'municipio': data['municipio']},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Institucion: {data["codigo"]} - {data["nombre"][:40]}'))
            creadas.append(obj)
        return creadas

    def _crear_programas(self):
        creados = []
        for data in PROGRAMAS_DEMO:
            obj, created = ProgramaTecnico.objects.get_or_create(
                codigo=data['codigo'],
                defaults={'nombre': data['nombre']},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Programa: {data["codigo"]} - {data["nombre"]}'))
            creados.append(obj)
        return creados

    def _crear_instructores(self, tipo_cc):
        instructores = []
        for i in range(10):
            nombres = random.choice(NOMBRES_COLOMBIANOS)
            apellido1 = random.choice(APELLIDOS_COLOMBIANOS)
            apellido2 = random.choice(APELLIDOS_COLOMBIANOS)
            apellidos = f'{apellido1} {apellido2}'
            cedula = str(random.randint(10_000_000, 80_000_000))

            persona, _ = Persona.objects.get_or_create(
                tipo_identificacion=tipo_cc,
                numero_identificacion=cedula,
                defaults={
                    'nombres': nombres,
                    'apellidos': apellidos,
                    'correo': f'instructor{i+1}@demoferia.edu.co',
                    'telefono': f'3{random.randint(100000000, 599999999)}',
                    'tipo_persona': 'INSTRUCTOR',
                }
            )

            instructor, created = Instructor.objects.get_or_create(persona=persona, defaults={'activo': True})
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Instructor: {persona.nombre_completo} CC {cedula}'))
            instructores.append(instructor)
        return instructores

    def _crear_proyectos(self, evento, instituciones, programas, instructores):
        proyectos = []
        idx = 0
        for i in range(20):
            codigo = f'PROY-{i+1:03d}'
            institucion = instituciones[i % len(instituciones)]
            programa = programas[i % len(programas)]
            instructor = instructores[i % len(instructores)]
            idx += 1

            proyecto, created = Proyecto.objects.get_or_create(
                evento=evento,
                codigo=codigo,
                defaults={
                    'nombre': f'Proyecto Demo {codigo} - {programa.nombre.title()}',
                    'descripcion': f'Proyecto demostrativo del programa {programa.nombre} de la institución {institucion.nombre}. Desarrollado en el marco de la Feria de Proyectos Productivos 2026.',
                    'institucion': institucion,
                    'programa': programa,
                    'instructor_responsable': instructor,
                    'estado': 'APROBADO',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Proyecto: {codigo} - {programa.nombre}'))
            proyectos.append(proyecto)
        return proyectos

    def _crear_aprendices(self, proyectos, tipos_id_lista):
        creados = 0
        for i in range(100):
            proyecto = proyectos[i % len(proyectos)]
            nombres = random.choice(NOMBRES_COLOMBIANOS)
            apellido1 = random.choice(APELLIDOS_COLOMBIANOS)
            apellido2 = random.choice(APELLIDOS_COLOMBIANOS)
            apellidos = f'{apellido1} {apellido2}'
            tipo_id = random.choice(tipos_id_lista)
            cedula = str(random.randint(1_000_000, 9_999_999))

            persona, p_created = Persona.objects.get_or_create(
                tipo_identificacion=tipo_id,
                numero_identificacion=cedula,
                defaults={
                    'nombres': nombres,
                    'apellidos': apellidos,
                    'correo': f'aprendiz{i+1}@demoferia.edu.co',
                    'tipo_persona': 'APRENDIZ',
                }
            )

            _, a_created = Aprendiz.objects.get_or_create(
                persona=persona,
                defaults={'proyecto': proyecto, 'grado': '11'},
            )
            if a_created:
                creados += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ Aprendices creados: {creados} (asignados a 20 proyectos)'))

    def _crear_invitados(self, tipo_cc):
        for idx, (entidad, cargo) in enumerate(ENTIDADES_INVITADOS):
            nombres = random.choice(NOMBRES_COLOMBIANOS)
            apellido1 = random.choice(APELLIDOS_COLOMBIANOS)
            apellido2 = random.choice(APELLIDOS_COLOMBIANOS)
            apellidos = f'{apellido1} {apellido2}'
            cedula = str(random.randint(10_000_000, 70_000_000))

            persona, _ = Persona.objects.get_or_create(
                tipo_identificacion=tipo_cc,
                numero_identificacion=cedula,
                defaults={
                    'nombres': nombres,
                    'apellidos': apellidos,
                    'correo': f'invitado{idx+1}@demoferia.edu.co',
                    'telefono': f'3{random.randint(100000000, 599999999)}',
                    'tipo_persona': 'INVITADO',
                }
            )

            _inv_defaults = {'entidad': entidad, 'cargo': cargo}
            try:
                Invitado._meta.get_field('activo')
                _inv_defaults['activo'] = True
            except Exception:
                pass
            _, created = Invitado.objects.get_or_create(
                persona=persona,
                defaults=_inv_defaults,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Invitado: {persona.nombre_completo[:30]} ({entidad})'))

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('============================================================')
        self.stdout.write('  SEED DEMO - SISTEMA FERIA DE PROYECTOS PRODUCTIVOS SENA')
        self.stdout.write('============================================================')
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[1/9] Creando roles iniciales...'))
        call_command('crear_roles_iniciales')
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[2/9] Creando usuarios demo (password: DemoSena1234*)...'))
        self._crear_usuarios_demo()
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[3/9] Creando Tipos de Identificación (CC, TI, PPT)...'))
        self._crear_tipos_identificacion()
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[4/9] Creando Evento demo ACTIVO...'))
        evento = self._crear_evento_demo()
        self._crear_tipos_servicio(evento)
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[5/9] Creando Instituciones Educativas y Programas Técnicos...'))
        instituciones = self._crear_instituciones()
        programas = self._crear_programas()
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[6/9] Creando Instructores...'))
        tipo_cc = TipoIdentificacion.objects.get(codigo='CC')
        instructores = self._crear_instructores(tipo_cc)
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[7/9] Creando 20 Proyectos cruzando I+P+I (PROY-001..PROY-020)...'))
        proyectos = self._crear_proyectos(evento, instituciones, programas, instructores)
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[8/9] Creando 100 Aprendices asignados a proyectos...'))
        tipo_ti = TipoIdentificacion.objects.get(codigo='TI')
        self._crear_aprendices(proyectos, [tipo_cc, tipo_ti])
        self.stdout.write('')

        self.stdout.write(self.style.MIGRATE_HEADING('[9/9] Creando Invitados con entidades...'))
        self._crear_invitados(tipo_cc)
        self.stdout.write('')

        self.stdout.write('============================================================')
        self.stdout.write(self.style.SUCCESS(
            '✅ SEED DEMO COMPLETADO. '
            'Usuarios demo: admin_demo / registro_demo / asistencia_demo / '
            'refrigerio_demo / certificado_demo / consulta_demo | '
            'Password demo: DemoSena1234*'
        ))
        self.stdout.write('============================================================')
        self.stdout.write('')
