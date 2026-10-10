from django.urls import path

from apps.usuarios.views import PerfilView, CustomLoginView, CambiarClaveView

app_name = 'usuarios'

urlpatterns = [
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/cambiar-clave/', CambiarClaveView.as_view(), name='cambiar_clave'),
    path('login/', CustomLoginView.as_view(), name='login'),
]

