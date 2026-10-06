from django.urls import path

from apps.refrigerios import views

app_name = 'refrigerios'

urlpatterns = [
    path('ingreso/', views.IngresoOperadorView.as_view(), name='ingreso'),
    path('api/validar-token/', views.ValidarTokenServicioJson.as_view(), name='api_validar'),
    path('api/registrar/', views.RegistrarEntregaServicioJson.as_view(), name='api_registrar'),
    path('buscar-persona/', views.BuscarManualServicioView.as_view(), name='buscar_manual'),
]
