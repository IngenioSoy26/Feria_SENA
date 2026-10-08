from django import forms
from .models import InstitucionEducativa, Municipio


class InstitucionForm(forms.ModelForm):
    municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.filter(activo=True).order_by('departamento', 'nombre'),
        label='Municipio',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = InstitucionEducativa
        fields = [
            'nombre', 'municipio', 'secretaria_educacion',
            'telefono', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la institución (MAYÚSCULA automática)'
            }),
            'secretaria_educacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Secretaría de Educación'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono (opcional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'activo' and field_name != 'municipio':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
                else:
                    if 'form-control' not in field.widget.attrs['class']:
                        field.widget.attrs['class'] += ' form-control'
