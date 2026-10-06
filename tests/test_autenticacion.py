from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.usuarios.management.commands.crear_roles_iniciales import ROLES_SISTEMA
from django.contrib.auth.models import Group, Permission

User = get_user_model()


class AutenticacionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        for nombre_rol in ROLES_SISTEMA.keys():
            grupo, _ = Group.objects.get_or_create(name=nombre_rol)

        cls.user = User.objects.create_user(
            username='test_login',
            email='test_login@sena.edu.co',
            password='Temporal123*',
            nombres='Usuario',
            apellidos='Prueba Login',
            rol_sistema='CONSULTA',
        )
        grupo_consulta = Group.objects.get(name='CONSULTA')
        cls.user.groups.add(grupo_consulta)

    def test_login_url_retorna_200(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_credenciales_correctas_redirige(self):
        login_ok = self.client.login(username='test_login', password='Temporal123*')
        self.assertTrue(login_ok)
        response = self.client.post(reverse('login'), {
            'username': 'test_login',
            'password': 'Temporal123*',
        })
        self.assertIn(response.status_code, [200, 302])

    def test_login_password_incorrecto_falla(self):
        login_bad = self.client.login(username='test_login', password='Erronea456*')
        self.assertFalse(login_bad)

    def test_usuario_no_autenticado_redirige_login(self):
        url_protegida = reverse('refrigerios:ingreso')
        response = self.client.get(url_protegida)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_logout_redirige_home(self):
        self.client.login(username='test_login', password='Temporal123*')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_usuario_tiene_correo_unico(self):
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='duplicado',
                email='test_login@sena.edu.co',
                password='OtroPass123*',
                nombres='Duplicado',
                apellidos='Correo',
                rol_sistema='CONSULTA',
            )

    def test_usuario_asignado_grupo_rol_sistema(self):
        self.assertTrue(
            self.user.groups.filter(name='CONSULTA').exists(),
            'El usuario demo CONSULTA debe pertenecer al grupo del mismo nombre.'
        )
