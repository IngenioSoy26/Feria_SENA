from django.urls import path

from .views import (
    ReportesIndexView,
    reportes_salud,
    participantes_excel_view,
    asistentes_excel_view,
    ausentes_excel_view,
    certificados_excel_view,
    refrigerios_excel_view,
    proyectos_excel_view,
    instituciones_excel_view,
    programas_excel_view,
    proyectos_detalle_excel_view,
    instructores_consolidado_excel_view,
    reporte_general_excel_view,
    reporte_general_pdf_view,
    importacion_form_view,
)

app_name = 'reportes'

urlpatterns = [
    path('', ReportesIndexView.as_view(), name='index'),
    path('participantes.xlsx', participantes_excel_view, name='participantes_excel'),
    path('asistentes.xlsx', asistentes_excel_view, name='asistentes_excel'),
    path('ausentes.xlsx', ausentes_excel_view, name='ausentes_excel'),
    path('certificados.xlsx', certificados_excel_view, name='certificados_excel'),
    path('refrigerios.xlsx', refrigerios_excel_view, name='refrigerios_excel'),
    path('proyectos.xlsx', proyectos_excel_view, name='proyectos_excel'),
    path('instituciones.xlsx', instituciones_excel_view, name='instituciones_excel'),
    path('programas.xlsx', programas_excel_view, name='programas_excel'),
    path('proyectos_detalle.xlsx', proyectos_detalle_excel_view, name='proyectos_detalle_excel'),
    path('instructores_consolidado.xlsx', instructores_consolidado_excel_view, name='instructores_consolidado_excel'),
    path('reporte_general.xlsx', reporte_general_excel_view, name='reporte_general_excel'),
    path('reporte_general.pdf', reporte_general_pdf_view, name='reporte_general_pdf'),
    path('importacion/', importacion_form_view, name='importacion_form'),
    path('health/', reportes_salud, name='health'),
]
