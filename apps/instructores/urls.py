from django.urls import path
from . import views

app_name = 'instructores'

urlpatterns = [
    path('', views.InstructorListView.as_view(), name='list'),
    path('new/', views.InstructorCreateView.as_view(), name='create'),
    path('<int:pk>/', views.InstructorDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.InstructorUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.InstructorDeleteView.as_view(), name='delete'),
]
