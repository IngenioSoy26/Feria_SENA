from django.contrib import admin
from .models import Visitante


@admin.register(Visitante)
class VisitanteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'entidad', 'cargo', 'persona_doc')
    list_select_related = ('persona', 'persona__tipo_identificacion')
    search_fields = ('persona__nombres', 'persona__apellidos', 'persona__numero_identificacion', 'entidad', 'cargo')

    def persona_doc(self, obj):
        try:
            ti = obj.persona.tipo_identificacion.codigo if obj.persona and obj.persona.tipo_identificacion else ''
            return f"{ti} {obj.persona.numero_identificacion}"
        except Exception:
            return ''
    persona_doc.short_description = 'Documento'
