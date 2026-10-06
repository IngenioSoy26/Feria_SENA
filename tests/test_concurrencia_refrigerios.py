import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.test import TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.usuarios.management.commands.crear_roles_iniciales import ROLES_SISTEMA
from apps.eventos.models import Evento, TipoIdentificacion, TipoServicio
from apps.personas.models import Persona
from apps.refrigerios.models import EntregaServicio

User = get_user_model()


class ConcurrenciaRefrigeriosTests(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        for nombre_rol in ROLES_SISTEMA.keys():
            Group.objects.get_or_create(name=nombre_rol)

        grupo_refri = Group.objects.get(name='OPERADOR_REFRIGERIO')

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.refrigerios.models import EntregaServicio
        ct = ContentType.objects.get_for_model(EntregaServicio)
        perm_add, _ = Permission.objects.get_or_create(
            codename='add_entregaservicio',
            content_type=ct,
            defaults={'name': 'Can add entrega servicio'},
        )
        grupo_refri.permissions.add(perm_add)

        self.operador = User.objects.create_user(
            username='op_concurrente',
            email='op_concurrente@senaferia.edu.co',
            password='DemoConcurrencia123*',
            nombres='Operador',
            apellidos='Concurrente',
            rol_sistema='OPERADOR_REFRIGERIO',
        )
        self.operador.groups.add(grupo_refri)

        self.tipo_cc, _ = TipoIdentificacion.objects.get_or_create(
            codigo='CC',
            defaults={'nombre': 'Cédula de Ciudadanía', 'activo': True},
        )

        self.evento, _ = Evento.objects.get_or_create(
            nombre='EVENTO CONCURRENCIA REFRI',
            defaults={
                'fecha_inicio': '2026-11-20',
                'fecha_fin': '2026-11-22',
                'lugar': 'Coliseo',
                'municipio': 'Riohacha',
                'regional': 'Guajira',
                'estado': 'ACTIVO',
                'activo': True,
            },
        )

        self.servicio, _ = TipoServicio.objects.get_or_create(
            evento=self.evento,
            nombre='Almuerzo Test Concurrente',
            defaults={'orden': 1, 'activo': True},
        )

        self.persona, _ = Persona.objects.get_or_create(
            tipo_identificacion=self.tipo_cc,
            numero_identificacion='99999999',
            defaults={
                'nombres': 'Persona',
                'apellidos': 'Concurrente',
                'correo': 'concurrente@senaferia.edu.co',
                'tipo_persona': 'APRENDIZ',
            },
        )

    def _hacer_request_post(self, operador, csrf_str=''):
        from django.test.client import Client
        import django.db.utils
        cliente = Client()
        cliente.force_login(operador)
        url = reverse('refrigerios:api_registrar')
        payload = {
            'persona_id': self.persona.id,
            'evento_id': self.evento.id,
            'tipo_servicio_id': self.servicio.id,
            'medio': 'MANUAL',
        }
        ultimo_error = None
        for intento in range(3):
            try:
                return cliente.post(
                    url,
                    data=json.dumps(payload),
                    content_type='application/json',
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                )
            except django.db.utils.OperationalError as exc:
                ultimo_error = exc
                import time
                time.sleep(0.2)
        return ultimo_error

    def test_dos_threads_mismo_refrigerio_misma_persona_solo_una_entrega(self):
        total_entregas_antes = EntregaServicio.objects.filter(
            evento=self.evento,
            persona=self.persona,
            tipo_servicio=self.servicio,
        ).count()
        self.assertEqual(total_entregas_antes, 0)

        resultados = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [
                pool.submit(self._hacer_request_post, self.operador),
                pool.submit(self._hacer_request_post, self.operador),
            ]
            for f in as_completed(futuros):
                try:
                    resp = f.result(timeout=30)
                    resultados.append(resp)
                except Exception as exc:
                    resultados.append(exc)

        entregas_ahora = EntregaServicio.objects.filter(
            evento=self.evento,
            persona=self.persona,
            tipo_servicio=self.servicio,
        ).count()

        self.assertEqual(
            entregas_ahora, 1,
            f'SE DEBE GARANTIZAR 1 SOLA EntregaServicio por la UniqueConstraint. '
            f'Se encontraron {entregas_ahora}. Resultados: {resultados}'
        )

        estados = []
        for r in resultados:
            if hasattr(r, 'json'):
                try:
                    data = r.json()
                    estados.append(data.get('status', '??'))
                except Exception:
                    estados.append(f'HTTP_{r.status_code}')
            else:
                estados.append('SQLITE_LOCK_RETRY')

        self.assertIn('VERDE', estados, 'Al menos una solicitud debe dar VERDE (primera entrega).')
        tuvo_amarillo_o_retry = ('AMARILLO' in estados) or ('SQLITE_LOCK_RETRY' in estados) or any(
            e.startswith('HTTP_') for e in estados
        )
        self.assertTrue(tuvo_amarillo_o_retry, f'Segunda solicitud debe ser AMARILLO o fallo SQLite (protegido por UniqueConstraint). Estados: {estados}')

