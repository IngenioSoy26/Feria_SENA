from django.urls import path
from . import views

app_name = 'proyectos'

urlpatterns = [
    path('', views.ProyectoListView.as_view(), name='list'),
    path('new/', views.ProyectoCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProyectoDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProyectoUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ProyectoDeleteView.as_view(), name='delete'),

    path('fichas/', views.FichaListView.as_view(), name='ficha_list'),
    path('fichas/new/', views.FichaCreateView.as_view(), name='ficha_create'),
    path('fichas/<int:pk>/', views.FichaDetailView.as_view(), name='ficha_detail'),
    path('fichas/<int:pk>/edit/', views.FichaUpdateView.as_view(), name='ficha_update'),
    path('fichas/<int:pk>/delete/', views.FichaDeleteView.as_view(), name='ficha_delete'),
]
