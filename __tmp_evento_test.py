import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from django.test.client import Client
from apps.usuarios.models import Usuario

if not Usuario.objects.filter(username='test_admin').exists():
    u = Usuario.objects.create_user(
        username='test_admin',
        email='test_admin@local.com',
        password='Demo12345*',
    )
    u.nombres = 'TEST'
    u.apellidos = 'ADMIN'
    u.rol_sistema = 'ADMINISTRADOR'
    u.is_staff = True
    u.is_superuser = True
    u.is_active = True
    u.save()
else:
    u = Usuario.objects.get(username='test_admin')
    u.set_password('Demo12345*')
    u.save()

c = Client()
ok = c.login(username='test_admin', password='Demo12345*')
print('Login OK:', ok)

r = c.get('/admin-seguro-sena-2026/eventos/evento/add/')
print('STATUS:', r.status_code)
print('Content len:', len(r.content))
if r.status_code != 200:
    from django.utils.encoding import force_str
    body = force_str(r.content, errors='replace')
    print(body[-3000:])
