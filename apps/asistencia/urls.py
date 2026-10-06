from django.urls import path
from django.template.response import TemplateResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.core.mixins import RoleRequiredMixin

app_name = 'asistencia'


class IngresoAsistenciaView(RoleRequiredMixin, LoginRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'OPERADOR_ASISTENCIA', 'REGISTRO']
    template_name = 'asistencia/ingreso.html'

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, self.template_name, {})


urlpatterns = [
    path('ingreso/', IngresoAsistenciaView.as_view(), name='ingreso'),
]
