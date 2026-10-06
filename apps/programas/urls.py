from django.urls import path
from . import views

app_name = 'programas'

urlpatterns = [
    path('', views.ProgramaListView.as_view(), name='list'),
    path('new/', views.ProgramaCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProgramaDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProgramaUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ProgramaDeleteView.as_view(), name='delete'),
]
