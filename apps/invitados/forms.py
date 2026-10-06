from django import forms
from .models import Invitado


class InvitadoForm(forms.ModelForm):
    class Meta:
        model = Invitado
        fields = ['persona', 'entidad', 'cargo']
        widgets = {
            'persona': forms.Select(attrs={'class': 'form-select'}),
            'entidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Empresa o entidad a la que pertenece'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo dentro de la entidad'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.personas.models import Persona
        self.fields['persona'].queryset = Persona.objects.filter(
            tipo_persona__in=['INVITADO', 'ORGANIZADOR']
        ).select_related('tipo_identificacion').order_by('apellidos', 'nombres')

        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ == 'Select':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-select'
            else:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
