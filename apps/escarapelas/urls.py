from django.urls import path

from apps.escarapelas import views

app_name = 'escarapelas'

urlpatterns = [
    path('', views.EscarapelaInicioView.as_view(), name='listar'),
    path('descargar/individual/<int:persona_id>/', views.EscarapelaDescargaIndividualView.as_view(), name='descargar_individual'),
    path('descargar/proyecto/<int:proyecto_id>/', views.EscarapelaDescargaProyectoView.as_view(), name='descargar_proyecto'),
    path('descargar/institucion/<int:institucion_id>/', views.EscarapelaDescargaInstitucionView.as_view(), name='descargar_institucion'),
    path('descargar/programa/<int:programa_id>/', views.EscarapelaDescargaProgramaView.as_view(), name='descargar_programa'),
    path('descargar/tipo/<str:tipo>/', views.EscarapelaDescargaTipoView.as_view(), name='descargar_tipo'),
    path('descargar/completo/', views.EscarapelaDescargaCompletaView.as_view(), name='descargar_completo'),
    path('descargar/completo/<int:evento_id>/', views.EscarapelaDescargaCompletaView.as_view(), name='descargar_completo_id'),
]
