from django import forms
from .models import Evento, TipoIdentificacion, TipoServicio


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'lugar', 'municipio', 'regional', 'estado', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del evento'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción del evento'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'lugar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lugar de realización'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipio'}),
            'regional': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Regional SENA'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['activo', 'estado']:
                if field.widget.__class__.__name__ != 'Select':
                    if 'class' not in field.widget.attrs:
                        field.widget.attrs['class'] = 'form-control'
            if field_name == 'estado' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select'

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        return cleaned_data


class TipoIdentificacionForm(forms.ModelForm):
    class Meta:
        model = TipoIdentificacion
        fields = ['codigo', 'nombre', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: CC, TI, CE'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Cédula de Ciudadanía'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'activo':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'


class TipoServicioForm(forms.ModelForm):
    class Meta:
        model = TipoServicio
        fields = ['nombre', 'orden', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Registro, Refrigerio'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'activo':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
