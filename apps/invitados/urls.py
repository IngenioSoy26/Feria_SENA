from django.urls import path
from . import views

app_name = 'invitados'

urlpatterns = [
    path('', views.InvitadoListView.as_view(), name='list'),
    path('new/', views.InvitadoCreateView.as_view(), name='create'),
    path('<int:pk>/', views.InvitadoDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.InvitadoUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.InvitadoDeleteView.as_view(), name='delete'),
]
