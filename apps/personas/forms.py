from django import forms
from apps.proyectos.models import Proyecto
from .models import Persona


class PersonaForm(forms.ModelForm):
    crear_perfil = forms.BooleanField(
        required=False,
        initial=True,
        label='Crear perfil asociado',
        help_text='Marque para crear el perfil de Aprendiz, Instructor, Invitado u Organizador según el tipo seleccionado.',
    )
    entidad = forms.CharField(
        required=False,
        max_length=200,
        label='Entidad (Invitado)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entidad que representa'}),
    )
    cargo = forms.CharField(
        required=False,
        max_length=150,
        label='Cargo (Invitado)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo dentro de la entidad'}),
    )
    programas = forms.ModelMultipleChoiceField(
        required=False,
        queryset=None,
        label='Programas (Instructor)',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '4'}),
    )
    proyecto = forms.ModelChoiceField(
        required=False,
        queryset=None,
        label='Proyecto (Aprendiz)',
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='-- Seleccione un proyecto (opcional) --',
    )
    grado = forms.CharField(
        required=False,
        max_length=10,
        initial='11',
        label='Grado (Aprendiz)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 11, 10, Postgrado'}),
    )
    cargo_organizador = forms.CharField(
        required=False,
        max_length=150,
        label='Cargo (Organizador)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Coordinador General, Logística, Registro'
        }),
    )
    area_organizador = forms.CharField(
        required=False,
        max_length=200,
        label='Área / Punto de atención (Organizador)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Ingreso Principal, Palcos, Mesa Central'
        }),
    )

    class Meta:
        model = Persona
        fields = [
            'tipo_identificacion', 'numero_identificacion',
            'nombres', 'apellidos', 'correo', 'telefono',
            'tipo_persona', 'activo',
        ]
        widgets = {
            'tipo_identificacion': forms.Select(attrs={'class': 'form-select'}),
            'numero_identificacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de documento'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer y segundo nombre'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer y segundo apellido'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de contacto'}),
            'tipo_persona': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.programas.models import ProgramaTecnico

        self.fields['programas'].queryset = ProgramaTecnico.objects.filter(activo=True).order_by('nombre')
        self.fields['proyecto'].queryset = Proyecto.objects.select_related(
            'evento', 'institucion'
        ).order_by('-fecha_creacion')

        for field_name, field in self.fields.items():
            if field_name not in ['activo', 'crear_perfil', 'programas', 'proyecto']:
                if field.widget.__class__.__name__ == 'Select':
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = 'form-select'
                elif field.widget.__class__.__name__ == 'SelectMultiple':
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = 'form-select'
                else:
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        tipo_persona = cleaned_data.get('tipo_persona')
        crear_perfil = cleaned_data.get('crear_perfil')

        if crear_perfil:
            if tipo_persona == 'INVITADO':
                if not cleaned_data.get('entidad'):
                    self.add_error('entidad', 'La entidad es requerida para crear perfil de Invitado.')
                if not cleaned_data.get('cargo'):
                    self.add_error('cargo', 'El cargo es requerido para crear perfil de Invitado.')
        return cleaned_data
