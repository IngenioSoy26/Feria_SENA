from django import forms
from .models import Instructor


class InstructorForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ['persona', 'programas', 'activo']
        widgets = {
            'persona': forms.Select(attrs={'class': 'form-select'}),
            'programas': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '6'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.personas.models import Persona
        from apps.programas.models import ProgramaTecnico

        self.fields['persona'].queryset = Persona.objects.filter(
            tipo_persona__in=['INSTRUCTOR', 'ORGANIZADOR']
        ).select_related('tipo_identificacion').order_by('apellidos', 'nombres')
        self.fields['programas'].queryset = ProgramaTecnico.objects.filter(
            activo=True
        ).order_by('nombre')

        for field_name, field in self.fields.items():
            if field_name != 'activo':
                if field.widget.__class__.__name__ in ['Select', 'SelectMultiple']:
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = 'form-select'
