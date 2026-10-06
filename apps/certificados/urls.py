from django.urls import path

from apps.certificados import views

app_name = 'certificados'

urlpatterns = [
    path('entrega/', views.EntregaOperadorView.as_view(), name='entrega'),
    path('api/validar-token/', views.ValidarTokenCertificadoJson.as_view(), name='api_validar'),
    path('api/registrar/', views.RegistrarEntregaCertificadoJson.as_view(), name='api_registrar'),
    path('buscar-persona/', views.BuscarManualCertificadoView.as_view(), name='buscar_manual'),
]
