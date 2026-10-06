from django.urls import path

from apps.core.views import HomeView, OfflineView, BusquedaRapidaView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('offline/', OfflineView.as_view(), name='offline'),
    path('api/busqueda-rapida/', BusquedaRapidaView.as_view(), name='busqueda_rapida'),
]
