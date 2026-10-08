from django.urls import path
from . import views

app_name = 'organizadores'

urlpatterns = [
    path('', views.OrganizadorListView.as_view(), name='list'),
    path('nuevo/', views.OrganizadorCreateView.as_view(), name='create'),
    path('<int:pk>/', views.OrganizadorDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.OrganizadorUpdateView.as_view(), name='update'),
    path('<int:pk>/eliminar/', views.OrganizadorDeleteView.as_view(), name='delete'),
]
