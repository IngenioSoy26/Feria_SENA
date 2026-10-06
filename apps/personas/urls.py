from django.urls import path
from . import views

app_name = 'personas'

urlpatterns = [
    path('', views.PersonaListView.as_view(), name='list'),
    path('new/', views.PersonaCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PersonaDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PersonaUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.PersonaDeleteView.as_view(), name='delete'),
]
