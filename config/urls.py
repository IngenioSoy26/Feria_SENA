import os

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from apps.usuarios.views import CustomLoginView, PerfilView, CambiarClaveView


class _GetLogoutView(auth_views.LogoutView):
    """Logout que acepta GET y POST.

    GET es necesario para los enlaces de "Cerrar sesión" que aparecen en
    páginas de error (403/404/500), donde el token CSRF puede no estar
    disponible. Para el resto de la interfaz se usa POST con CSRF.
    """
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

DJANGO_ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin/')

urlpatterns = [
    path(DJANGO_ADMIN_URL, admin.site.urls),

    path('', include('apps.core.simple_urls', namespace='simple')),
    path('core/', include('apps.core.urls', namespace='core')),
    path('usuarios/', include('apps.usuarios.urls', namespace='usuarios')),
    path('eventos/', include('apps.eventos.urls', namespace='eventos')),
    path('instituciones/', include('apps.instituciones.urls', namespace='instituciones')),
    path('programas/', include('apps.programas.urls', namespace='programas')),
    path('personas/', include('apps.personas.urls', namespace='personas')),
    path('proyectos/', include('apps.proyectos.urls', namespace='proyectos')),
    path('instructores/', include('apps.instructores.urls', namespace='instructores')),
    path('invitados/', include('apps.invitados.urls', namespace='invitados')),
    path('organizadores/', include('apps.organizadores.urls', namespace='organizadores')),
    path('escarapelas/', include('apps.escarapelas.urls', namespace='escarapelas')),
    path('asistencia/', include('apps.asistencia.urls', namespace='asistencia')),
    path('refrigerios/', include('apps.refrigerios.urls', namespace='refrigerios')),
    path('certificados/', include('apps.certificados.urls', namespace='certificados')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('reportes/', include('apps.reportes.urls', namespace='reportes')),
    path('auditoria/', include('apps.auditoria.urls', namespace='auditoria')),

    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', _GetLogoutView.as_view(), name='logout'),
    path('accounts/profile/', PerfilView.as_view(), name='profile'),
    path('accounts/password_change/', CambiarClaveView.as_view(), name='password_change'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
