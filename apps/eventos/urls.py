from django.urls import path
from . import views

app_name = 'eventos'

urlpatterns = [
    path('', views.EventoListView.as_view(), name='list'),
    path('new/', views.EventoCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EventoDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.EventoUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.EventoDeleteView.as_view(), name='delete'),
    path('<int:pk>/toggle-activo/', views.EventoToggleActivoView.as_view(), name='toggle_activo'),
    path('<int:evento_pk>/servicio/<int:servicio_pk>/toggle/', views.ServicioToggleActivoView.as_view(), name='servicio_toggle'),
    path('<int:evento_pk>/servicio/<int:servicio_pk>/delete/', views.ServicioDeleteView.as_view(), name='servicio_delete'),
    path('tipos-identificacion/', views.TipoIdentificacionListView.as_view(), name='tipos_identificacion_list'),
    path('tipos-identificacion/new/', views.TipoIdentificacionCreateView.as_view(), name='tipos_identificacion_create'),
    path('tipos-identificacion/<int:pk>/edit/', views.TipoIdentificacionUpdateView.as_view(), name='tipos_identificacion_update'),
]
