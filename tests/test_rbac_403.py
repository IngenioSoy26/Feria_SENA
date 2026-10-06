from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.usuarios.management.commands.crear_roles_iniciales import ROLES_SISTEMA

User = get_user_model()


def _crear_usuario(username, rol, password='DemoRbac123*'):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@senaferia.edu.co',
        password=password,
        nombres=rol.title(),
        apellidos='Demo RBAC',
        rol_sistema=rol,
    )
    grupo, _ = Group.objects.get_or_create(name=rol)
    user.groups.add(grupo)
    return user


class Rbac403Tests(TestCase):

    @classmethod
    def setUpTestData(cls):
        for nombre_rol in ROLES_SISTEMA.keys():
            Group.objects.get_or_create(name=nombre_rol)

        cls.op_asistencia = _crear_usuario('op_asistencia_test', 'OPERADOR_ASISTENCIA')
        cls.op_refrigerio = _crear_usuario('op_refrigerio_test', 'OPERADOR_REFRIGERIO')
        cls.op_certificado = _crear_usuario('op_certificado_test', 'OPERADOR_CERTIFICADO')
        cls.usuario_consulta = _crear_usuario('consulta_test', 'CONSULTA')
        cls.usuario_registro = _crear_usuario('registro_test', 'REGISTRO')

    # ---------- TEST 1 ----------
    def test_operador_asistencia_no_accede_refrigerios_ingreso(self):
        self.client.force_login(self.op_asistencia)
        url = reverse('refrigerios:ingreso')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 403,
            'OPERADOR_ASISTENCIA NO debe acceder a /refrigerios/ingreso/ → 403.'
        )

    # ---------- TEST 2 ----------
    def test_operador_refrigerio_no_accede_certificados_entrega(self):
        self.client.force_login(self.op_refrigerio)
        url = reverse('certificados:entrega')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 403,
            'OPERADOR_REFRIGERIO NO debe acceder a /certificados/entrega/ → 403.'
        )

    # ---------- TEST 3 ----------
    def test_consulta_no_puede_crear_institucion_post_403(self):
        self.client.force_login(self.usuario_consulta)
        url = reverse('instituciones:create')
        response = self.client.post(url, {
            'codigo': 'INS-RBAC-99',
            'nombre': 'Institucion No Permitida',
            'municipio': 'Riohacha',
        }, follow=True)
        esperados = {302, 403}
        if response.status_code == 200:
            ultimo = response.redirect_chain[-1][0] if response.redirect_chain else ''
            tiene_403 = any(status == 403 for _, status in response.redirect_chain)
            self.assertTrue(
                tiene_403 or '403' in ultimo or '403' in str(response.content[:500]),
                'CONSULTA NO debe poder hacer POST crear institución → 403.'
            )
        else:
            self.assertIn(
                response.status_code, esperados,
                'CONSULTA NO debe poder hacer POST crear institución → 403.'
            )

    # ---------- TEST 4 ----------
    def test_operador_asistencia_no_puede_crear_certificado_api(self):
        self.client.force_login(self.op_asistencia)
        url = reverse('certificados:api_registrar')
        response = self.client.post(
            url,
            data={'persona_id': 1, 'evento_id': 1},
            content_type='application/json',
        )
        self.assertIn(
            response.status_code, {403, 200},
            'OPERADOR_ASISTENCIA no debe tener permiso certificados.add_certificado → 403.'
        )
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(
                data.get('codigo') or (403 if 'Permiso' in str(data) else None),
                403,
                'API certificados debe retornar error 403 json si el usuario no tiene permiso.'
            )

    # ---------- TEST 5 ----------
    def test_operador_refrigerio_no_accede_asistencia_ingreso(self):
        self.client.force_login(self.op_refrigerio)
        url = reverse('asistencia:ingreso')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 403,
            'OPERADOR_REFRIGERIO NO debe acceder a /asistencia/ingreso/ → 403.'
        )

    # ---------- TEST 6 ----------
    def test_consulta_no_accede_personas_new_403(self):
        self.client.force_login(self.usuario_consulta)
        url = reverse('personas:create')
        response = self.client.get(url)
        status_codes_validos = {302, 403}
        self.assertIn(
            response.status_code, status_codes_validos,
            'CONSULTA no debe acceder a /personas/new/ → 403/302.'
        )
        if response.status_code == 302:
            destino = response.url or ''
            if '/accounts/login/' not in destino:
                self.fail('Redirección inesperada, se esperaba login o 403 directo.')
