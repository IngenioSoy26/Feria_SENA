from django import forms
from .models import InstitucionEducativa


class InstitucionForm(forms.ModelForm):
    class Meta:
        model = InstitucionEducativa
        fields = ['nombre', 'municipio', 'secretaria_educacion', 'codigo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la institución'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipio'}),
            'secretaria_educacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Secretaría de educación'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código único de institución'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'activo':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
                else:
                    if 'form-control' not in field.widget.attrs['class']:
                        field.widget.attrs['class'] += ' form-control'
