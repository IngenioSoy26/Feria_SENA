from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from apps.core.mixins import RoleRequiredMixin


class ReportesIndexView(RoleRequiredMixin, LoginRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'CONSULTA']

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, 'reportes/inicio.html', {})


class _ProximamenteView(RoleRequiredMixin, LoginRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'CONSULTA']
    volver = 'dashboard:principal'

    def get(self, request, *args, **kwargs):
        messages.info(
            request,
            'Reporte en mantenimiento. Próximamente podrá descargar el archivo Excel aquí; '
            'entretanto use la opción "Listados únicos" del menú principal.',
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/dashboard/'))


participantes_excel_view = _ProximamenteView.as_view()
asistentes_excel_view = _ProximamenteView.as_view()
certificados_excel_view = _ProximamenteView.as_view()
refrigerios_excel_view = _ProximamenteView.as_view()
proyectos_excel_view = _ProximamenteView.as_view()


def reportes_salud(request):
    return HttpResponse('OK reportes app', content_type='text/plain; charset=utf-8')
