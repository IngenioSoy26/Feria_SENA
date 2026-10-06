from django.urls import path

from .views import (
    ReportesIndexView,
    reportes_salud,
    participantes_excel_view,
    asistentes_excel_view,
    certificados_excel_view,
    refrigerios_excel_view,
    proyectos_excel_view,
)

app_name = 'reportes'

urlpatterns = [
    path('', ReportesIndexView.as_view(), name='index'),
    path('participantes.xlsx', participantes_excel_view, name='participantes_excel'),
    path('asistentes.xlsx', asistentes_excel_view, name='asistentes_excel'),
    path('certificados.xlsx', certificados_excel_view, name='certificados_excel'),
    path('refrigerios.xlsx', refrigerios_excel_view, name='refrigerios_excel'),
    path('proyectos.xlsx', proyectos_excel_view, name='proyectos_excel'),
    path('health/', reportes_salud, name='health'),
]
