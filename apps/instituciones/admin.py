from django.contrib import admin
from django.http import HttpResponse
from openpyxl import Workbook
from .models import InstitucionEducativa


@admin.register(InstitucionEducativa)
class InstitucionEducativaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'municipio', 'secretaria_educacion',
        'telefono', 'activo',
    ]
    list_filter = ['activo', 'municipio', 'secretaria_educacion']
    search_fields = ['nombre', 'codigo', 'municipio', 'secretaria_educacion', 'telefono']
    autocomplete_fields = []
    readonly_fields = ['codigo']
    list_per_page = 50
    ordering = ['municipio', 'nombre']
    list_display_links = ['codigo', 'nombre']
    list_editable = ['activo']
    prepopulated_fields = {}
    save_on_top = True
    actions = ['exportar_excel', 'activar_seleccionadas', 'desactivar_seleccionadas']
    fieldsets = (
        ('Información Básica (Obligatoria)', {
            'description': 'Código único automático, nombre oficial, municipio y secretaría de educación. El Código se genera automáticamente (no editable).',
            'fields': (
                ('codigo',),
                ('nombre',),
                ('municipio', 'secretaria_educacion'),
                'telefono',
            ),
        }),
        ('Datos Complementarios (Opcionales)', {
            'classes': ('collapse',),
            'fields': (
                ('tipo', 'zona', 'sector'),
                ('caracter', 'especialidad'),
                'direccion',
                'correo_institucional',
            ),
        }),
        ('Personal Directivo (Opcional)', {
            'classes': ('collapse',),
            'fields': (
                ('nombre_rector', 'telefono_rector'),
                ('nombre_coordinador', 'celular_coordinador'),
            ),
        }),
        ('Estado', {
            'fields': ('activo',),
        }),
    )

    @admin.action(description='📥 Exportar seleccionadas a Excel')
    def exportar_excel(self, request, queryset):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Instituciones Educativas'
        headers = [
            'CÓDIGO ÚNICO IE', 'NOMBRE', 'MUNICIPIO', 'SECRETARÍA EDUCACIÓN',
            'TELÉFONO', 'TIPO', 'ZONA', 'SECTOR', 'CARÁCTER', 'ESPECIALIDAD',
            'DIRECCIÓN', 'CORREO INSTITUCIONAL',
            'RECTOR', 'TELÉFONO RECTOR',
            'COORDINADOR', 'CELULAR COORDINADOR',
            'ACTIVO'
        ]
        ws.append(headers)
        for ie in queryset.order_by('municipio', 'nombre'):
            ws.append([
                ie.codigo or '',
                ie.nombre or '',
                ie.municipio or '',
                ie.secretaria_educacion or '',
                ie.telefono or '',
                ie.tipo or '',
                ie.zona or '',
                ie.sector or '',
                ie.caracter or '',
                ie.especialidad or '',
                ie.direccion or '',
                ie.correo_institucional or '',
                ie.nombre_rector or '',
                ie.telefono_rector or '',
                ie.nombre_coordinador or '',
                ie.celular_coordinador or '',
                'SI' if ie.activo else 'NO',
            ])
        for col_idx, _ in enumerate(headers, start=1):
            ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else 'A' + chr(64 + col_idx - 26)].width = 28
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="instituciones_educativas.xlsx"'
        wb.save(response)
        return response

    @admin.action(description='✔ Activar instituciones seleccionadas')
    def activar_seleccionadas(self, request, queryset):
        actualizados = queryset.update(activo=True)
        self.message_user(request, f'Se activaron {actualizados} institución(es) educativa(s).')

    @admin.action(description='✖ Desactivar instituciones seleccionadas')
    def desactivar_seleccionadas(self, request, queryset):
        actualizados = queryset.update(activo=False)
        self.message_user(request, f'Se desactivaron {actualizados} institución(es) educativa(s).')
