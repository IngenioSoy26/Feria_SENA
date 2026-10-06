from django.urls import path
from . import views

app_name = 'instituciones'

urlpatterns = [
    path('', views.InstitucionListView.as_view(), name='list'),
    path('new/', views.InstitucionCreateView.as_view(), name='create'),
    path('<int:pk>/', views.InstitucionDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.InstitucionUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.InstitucionDeleteView.as_view(), name='delete'),
]
