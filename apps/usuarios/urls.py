from django.urls import path

from apps.usuarios.views import PerfilView, CustomLoginView

app_name = 'usuarios'

urlpatterns = [
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('login/', CustomLoginView.as_view(), name='login'),
]
