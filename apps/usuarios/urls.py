from django.urls import path

from apps.usuarios.views import (
    PerfilView, CustomLoginView, CambiarClaveView,
    ListaRolesView, CrearEditarRolView, EliminarRolView,
)

app_name = 'usuarios'

urlpatterns = [
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/cambiar-clave/', CambiarClaveView.as_view(), name='cambiar_clave'),
    path('login/', CustomLoginView.as_view(), name='login'),
    # Gestión de roles y permisos
    path('roles/', ListaRolesView.as_view(), name='lista_roles'),
    path('roles/crear/', CrearEditarRolView.as_view(), name='crear_rol'),
    path('roles/editar/<int:pk>/', CrearEditarRolView.as_view(), name='editar_rol'),
    path('roles/eliminar/<int:pk>/', EliminarRolView.as_view(), name='eliminar_rol'),
]

