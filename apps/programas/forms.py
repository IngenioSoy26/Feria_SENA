from django import forms
from .models import ProgramaTecnico


class ProgramaForm(forms.ModelForm):
    class Meta:
        model = ProgramaTecnico
        fields = ['codigo', 'nombre', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código del programa'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del programa técnico'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'activo':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
