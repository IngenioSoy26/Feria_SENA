from django import forms
from .models import Proyecto, Aprendiz, Ficha


class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            'numero', 'institucion', 'programa', 'grado', 'municipio',
            'instructor_lider', 'telefono_instructor', 'correo_instructor',
            'fecha_inicio', 'fecha_fin', 'activo',
        ]
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de ficha (7 dígitos)'}),
            'institucion': forms.Select(attrs={'class': 'form-select'}),
            'programa': forms.Select(attrs={'class': 'form-select'}),
            'grado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 11, 10, Técnico'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipio'}),
            'instructor_lider': forms.Select(attrs={'class': 'form-select'}),
            'telefono_instructor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono de contacto'}),
            'correo_instructor': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.instituciones.models import InstitucionEducativa
        from apps.programas.models import ProgramaTecnico
        from apps.instructores.models import Instructor

        self.fields['institucion'].queryset = InstitucionEducativa.objects.filter(activo=True).order_by('nombre')
        self.fields['programa'].queryset = ProgramaTecnico.objects.filter(activo=True).order_by('nombre')
        self.fields['instructor_lider'].queryset = Instructor.objects.filter(
            activo=True
        ).select_related('persona').order_by('persona__apellidos')

        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ in ['Select', 'SelectMultiple']:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-select'
            elif field_name != 'activo':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = [
            'evento', 'codigo', 'nombre', 'descripcion',
            'institucion', 'programa', 'instructor_responsable', 'estado',
        ]
        widgets = {
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código único del proyecto'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proyecto productivo'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción del proyecto, objetivos, productos, etc.'}),
            'institucion': forms.Select(attrs={'class': 'form-select'}),
            'programa': forms.Select(attrs={'class': 'form-select'}),
            'instructor_responsable': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.eventos.models import Evento
        from apps.instituciones.models import InstitucionEducativa
        from apps.programas.models import ProgramaTecnico
        from apps.instructores.models import Instructor

        self.fields['evento'].queryset = Evento.objects.order_by('-fecha_inicio')
        self.fields['institucion'].queryset = InstitucionEducativa.objects.filter(activo=True).order_by('nombre')
        self.fields['programa'].queryset = ProgramaTecnico.objects.filter(activo=True).order_by('nombre')
        self.fields['instructor_responsable'].queryset = Instructor.objects.filter(
            activo=True
        ).select_related('persona').order_by('persona__apellidos')

        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ in ['Select', 'SelectMultiple']:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-select'
            elif field_name != 'activo':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'


class AgregarAprendizForm(forms.Form):
    persona = forms.ModelChoiceField(
        queryset=None,
        label='Seleccionar Persona',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Solo aparecen personas registradas como Aprendiz que aún no tienen proyecto.',
    )
    grado = forms.CharField(
        max_length=10,
        initial='11',
        label='Grado',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 11, 10, Técnico'}),
    )
    crear_persona = forms.BooleanField(
        required=False,
        label='¿La persona no existe aún?',
        help_text='Marque para guardar solo los datos básicos y crear el aprendiz luego desde Personas.',
    )
    nombres = forms.CharField(
        required=False,
        max_length=120,
        label='Nombres',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Si la persona no existe'}),
    )
    apellidos = forms.CharField(
        required=False,
        max_length=120,
        label='Apellidos',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    numero_identificacion = forms.CharField(
        required=False,
        max_length=30,
        label='N° Identificación',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, proyecto=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.personas.models import Persona

        qs_personas = Persona.objects.filter(
            tipo_persona='APRENDIZ',
            activo=True
        ).exclude(
            perfil_aprendiz__isnull=False
        ).select_related('tipo_identificacion').order_by('apellidos', 'nombres')

        self.fields['persona'].queryset = qs_personas
        self.fields['persona'].empty_label = '-- Seleccione una persona --'

    def clean(self):
        cleaned_data = super().clean()
        crear = cleaned_data.get('crear_persona')
        persona = cleaned_data.get('persona')

        if not crear and not persona:
            raise forms.ValidationError('Seleccione una persona o marque "La persona no existe aún".')

        if crear:
            for campo in ['nombres', 'apellidos', 'numero_identificacion']:
                if not cleaned_data.get(campo):
                    self.add_error(campo, f'{self.fields[campo].label} es requerido para crear la persona.')
        return cleaned_data
