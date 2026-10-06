from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.PrincipalView.as_view(), name='principal'),
    path('api/kpis/', views.KpisJsonView.as_view(), name='api_kpis'),
    path('api/graficos/', views.GraficosJsonView.as_view(), name='api_graficos'),
]
