from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from apps.core.mixins import RoleRequiredMixin
from .services.exportacion_excel import (
    reporte_participantes,
    reporte_asistentes,
    reporte_ausentes,
    reporte_refrigerios,
    reporte_certificados,
    reporte_instituciones,
    reporte_programas,
    reporte_proyectos,
    reporte_proyectos_detalle,
    reporte_instructores_consolidado,
    reporte_general_excel,
)


class ReportesIndexView(RoleRequiredMixin, LoginRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'CONSULTA', 'GERENTE', 'REGISTRO']

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, 'reportes/inicio.html', {})


class _ReporteExcelBase(RoleRequiredMixin, LoginRequiredMixin, View):
    """Vista base que llama a una función de generación de reporte."""
    roles_requeridos = ['ADMINISTRADOR', 'CONSULTA', 'GERENTE', 'REGISTRO']
    funcion = None  # asignar en subclases

    def get(self, request, *args, **kwargs):
        try:
            return self.funcion()
        except Exception as e:
            messages.error(
                request,
                f'Error al generar el reporte: {str(e)}',
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/reportes/'))


class ParticipantesExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_participantes)


class AsistentesExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_asistentes)


class AusentesExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_ausentes)


class RefrigeriosExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_refrigerios)


class CertificadosExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_certificados)


class InstitucionesExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_instituciones)


class ProgramasExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_programas)


class ProyectosExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_proyectos)


class ProyectosDetalleExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_proyectos_detalle)


class InstructoresConsolidadoExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_instructores_consolidado)


class ReporteGeneralExcelView(_ReporteExcelBase):
    funcion = staticmethod(reporte_general_excel)


class _ProximamenteView(RoleRequiredMixin, LoginRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'CONSULTA', 'GERENTE', 'REGISTRO']
    volver = 'dashboard:principal'

    def get(self, request, *args, **kwargs):
        messages.info(
            request,
            'Reporte en mantenimiento. Próximamente podrá descargar el archivo aquí.',
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/reportes/'))


# Vistas instanciadas para URLs
participantes_excel_view = ParticipantesExcelView.as_view()
asistentes_excel_view = AsistentesExcelView.as_view()
ausentes_excel_view = AusentesExcelView.as_view()
refrigerios_excel_view = RefrigeriosExcelView.as_view()
certificados_excel_view = CertificadosExcelView.as_view()
instituciones_excel_view = InstitucionesExcelView.as_view()
programas_excel_view = ProgramasExcelView.as_view()
proyectos_excel_view = ProyectosExcelView.as_view()
proyectos_detalle_excel_view = ProyectosDetalleExcelView.as_view()
instructores_consolidado_excel_view = InstructoresConsolidadoExcelView.as_view()
reporte_general_excel_view = ReporteGeneralExcelView.as_view()
reporte_general_pdf_view = _ProximamenteView.as_view()
importacion_form_view = _ProximamenteView.as_view()


def reportes_salud(request):
    return HttpResponse('OK reportes app', content_type='text/plain; charset=utf-8')
