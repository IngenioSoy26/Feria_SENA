from django.db.models import Q, Value
from django.db.models.functions import Concat, Coalesce
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic.base import TemplateView
from django.urls import reverse

from apps.core.mixins import AjaxLoginRequiredMixin
from apps.personas.models import Persona


def get_redirect_url_por_rol(user):
    if not hasattr(user, 'rol_sistema'):
        return reverse('login')
    rol = user.rol_sistema
    if rol in ('ADMINISTRADOR', 'REGISTRO', 'CONSULTA'):
        return reverse('dashboard:principal')
    if rol == 'OPERADOR_ASISTENCIA':
        return reverse('asistencia:ingreso')
    if rol == 'OPERADOR_REFRIGERIO':
        return reverse('refrigerios:entrega')
    if rol == 'OPERADOR_CERTIFICADO':
        return reverse('certificados:entrega')
    return reverse('login')


class HomeView(TemplateView):
    template_name = 'home.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        return redirect(get_redirect_url_por_rol(request.user))


class OfflineView(View):
    template_name = 'offline.html'

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, self.template_name, {})


class BusquedaRapidaView(AjaxLoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            data = request.POST
        query = (data.get('q') or data.get('query') or '').strip()
        if not query or len(query) < 2:
            return JsonResponse({'ok': True, 'resultados': []})

        qs = Persona.objects.select_related(
            'tipo_identificacion',
        ).prefetch_related(
            'perfil_aprendiz__proyecto__institucion',
        ).filter(
            activo=True
        ).annotate(
            nombre_completo=Concat(
                Coalesce('nombres', Value('')),
                Value(' '),
                Coalesce('apellidos', Value('')),
            )
        ).filter(
            Q(numero_identificacion__icontains=query)
            | Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(perfil_aprendiz__proyecto__nombre__icontains=query)
            | Q(perfil_aprendiz__proyecto__codigo__icontains=query)
            | Q(perfil_aprendiz__proyecto__institucion__nombre__icontains=query)
            | Q(perfil_aprendiz__proyecto__institucion__codigo__icontains=query)
        ).distinct()[:10]

        resultados = []
        for p in qs:
            rol = p.get_tipo_persona_display()
            proyecto = ''
            institucion = ''
            aprendiz = getattr(p, 'perfil_aprendiz', None)
            if aprendiz and aprendiz.proyecto:
                proyecto = str(aprendiz.proyecto)
                if aprendiz.proyecto.institucion:
                    institucion = aprendiz.proyecto.institucion.nombre
            resultados.append({
                'persona_id': p.id,
                'nombre': p.nombre_completo,
                'rol': rol,
                'institucion': institucion,
                'proyecto': proyecto,
            })

        return JsonResponse({'ok': True, 'resultados': resultados})
