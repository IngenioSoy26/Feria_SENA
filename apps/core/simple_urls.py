from django.urls import path
from django.conf import settings
from django.http import Http404
from apps.core import simple_views

app_name = 'simple'


def _token_valido(esperado):
    def _check(request, token_registro=None, token_operador=None, *a, **kw):
        tok = token_registro or token_operador
        if not esperado or tok != esperado:
            raise Http404('Enlace no válido. Solicita a un administrador el enlace actualizado.')
        return None
    return _check


# Rutas públicas token (no piden login)
_publicas = [
    path('r/<slug:token_registro>/registro/', simple_views.WizardRegistroView.as_view(), {'paso': 1}, name='public_wizard'),
    path('r/<slug:token_registro>/registro/<int:paso>/', simple_views.WizardRegistroView.as_view(), name='public_wizard_paso'),
    path('r/<slug:token_registro>/registro/personas/', simple_views.RegistroPersonasPublicView.as_view(), name='public_registro_personas'),
    path('r/<slug:token_registro>/registro/personas/gracias/<int:pk>/', simple_views.RegistroPersonasGraciasView.as_view(), name='public_registro_personas_gracias'),
    path('r/<slug:token_registro>/buscar/', simple_views.BuscarAjaxView.as_view(), name='public_buscar'),
    path('r/<slug:token_registro>/escarapela/<int:persona_id>/', simple_views.DescargarEscarapelaIndividual.as_view(), name='public_escarapela'),
    path('r/<slug:token_registro>/escarapelas/lote/<slug:grupo>/', simple_views.DescargarEscarapelasLote.as_view(), name='public_escarapelas_lote'),
    path('r/<slug:token_registro>/certificado/editar/<int:persona_id>/<slug:tipo>/', simple_views.EditarCertificadoView.as_view(), name='public_certificado_editar'),
    path('r/<slug:token_registro>/certificado/lote/<slug:tipo>/<slug:grupo>/', simple_views.DescargarCertificadosLoteView.as_view(), name='public_certificados_lote'),
    path('r/<slug:token_registro>/listados/<slug:que>/', simple_views.ListadoUnicosView.as_view(), name='public_listados'),
    path('r/<slug:token_registro>/dashboard/', simple_views.DashboardSimpleView.as_view(), name='public_dashboard'),

    path('o/<slug:token_operador>/<slug:tipo>/', simple_views.OperadorMobileView.as_view(), name='public_operador'),
    path('o/<slug:token_operador>/api/registrar/', simple_views.RegistrarOperadorAjax.as_view(), name='public_api_registrar'),
    path('o/<slug:token_operador>/api/stats/', simple_views.StatsOperadorAjax.as_view(), name='public_api_stats_operador'),
]


def _revisar_rutas_publicas():
    # Si TOKEN_REGISTRO_PUBLICO está vacío, las rutas públicas /r/ siguen existiendo PERO retornan 404 siempre.
    return


urlpatterns = [
    path('', simple_views.HomeSimpleView.as_view(), name='home'),

    path('panel-admin/', simple_views.PanelAdminDashboardView.as_view(), name='panel_admin'),
    path('importar-excel/', simple_views.ImportadorExcelView.as_view(), name='importador_excel'),
    path('api/stats-operativos/', simple_views.StatsOperativosAjax.as_view(), name='api_stats'),

    path('registro/', simple_views.WizardRegistroView.as_view(), {'paso': 1}, name='wizard'),
    path('registro/<int:paso>/', simple_views.WizardRegistroView.as_view(), name='wizard_paso'),
    path('registro/personas/', simple_views.RegistroPersonasPublicView.as_view(), name='registro_personas'),
    path('registro/personas/gracias/<int:pk>/', simple_views.RegistroPersonasGraciasView.as_view(), name='registro_personas_gracias'),
    path('buscar/', simple_views.BuscarAjaxView.as_view(), name='buscar'),

    path('operador/<slug:tipo>/', simple_views.OperadorMobileView.as_view(), name='operador'),
    path('operador/api/stats/', simple_views.StatsOperadorAjax.as_view(), name='api_stats_operador'),
    path('api/registrar/', simple_views.RegistrarOperadorAjax.as_view(), name='api_registrar'),

    path('dashboard/', simple_views.DashboardSimpleView.as_view(), name='dashboard'),
    path('listados/<slug:que>/', simple_views.ListadoUnicosView.as_view(), name='listados'),

    path('escarapela/<int:persona_id>/', simple_views.DescargarEscarapelaIndividual.as_view(), name='escarapela_persona'),
    path('escarapelas/lote/<slug:grupo>/', simple_views.DescargarEscarapelasLote.as_view(), name='escarapelas_lote'),

    path('certificado/editar/<int:persona_id>/<slug:tipo>/', simple_views.EditarCertificadoView.as_view(), name='certificado_editar'),
    path('certificado/lote/<slug:tipo>/<slug:grupo>/', simple_views.DescargarCertificadosLoteView.as_view(), name='certificados_lote'),
] + _publicas
