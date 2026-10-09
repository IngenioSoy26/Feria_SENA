import re
import secrets
import string

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

Usuario = get_user_model()


def generar_password_segura(longitud=10):
    alfabeto = string.ascii_letters + string.digits
    while True:
        pwd = ''.join(secrets.choice(alfabeto) for _ in range(longitud))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and sum(c.isdigit() for c in pwd) >= 2):
            return pwd


class UsuarioGestionForm(forms.ModelForm):
    ROLES_FORM = (
        ('', '⬇️ Selecciona un rol'),
        ('ADMINISTRADOR', '🛡 Administrador · acceso completo'),
        ('REGISTRO', '📝 Registro · proyectos y fichas'),
        ('GERENTE', '📊 Gerente · Dashboard y reportes'),
        ('OPERADOR_ASISTENCIA', '✅ Operador de Asistencia · QR'),
        ('OPERADOR_REFRIGERIO', '🍱 Operador de Refrigerio · almuerzo'),
        ('OPERADOR_CERTIFICADO', '📜 Operador de Certificado · entrega'),
        ('CONSULTA', '🔍 Consulta · solo lectura'),
    )

    password_auto = forms.BooleanField(
        label='Generar contraseña automáticamente',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class':'form-check-input lg-check-sena', 'id':'id_password_auto'}),
    )
    password_manual = forms.CharField(
        label='Contraseña manual (solo si NO es automática)',
        required=False,
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Mínimo 8 caracteres · si desactivaste generar automático',
            'autocomplete':'new-password'}),
    )
    enviar_correo = forms.BooleanField(
        label='Mostrar credenciales en pantalla (luego de guardar)',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class':'form-check-input lg-check-sena'}),
    )

    class Meta:
        model = Usuario
        fields = [
            'username', 'nombres', 'apellidos',
            'email', 'rol_sistema', 'activo',
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class':'form-control form-control-lg',
                'placeholder':'usuario · un mínimo 4 letras/números · sin espacios',
                'autocomplete':'off'}),
            'nombres': forms.TextInput(attrs={
                'class':'form-control form-control-lg up-case',
                'placeholder':'Primer y segundo nombre',
                'autocomplete':'off',
                'autocapitalize':'words'}),
            'apellidos': forms.TextInput(attrs={
                'class':'form-control form-control-lg up-case',
                'placeholder':'Primer y segundo apellido',
                'autocomplete':'off',
                'autocapitalize':'words'}),
            'email': forms.EmailInput(attrs={
                'class':'form-control form-control-lg',
                'placeholder':'correo@ejemplo.com · ÚNICO por usuario',
                'autocomplete':'off'}),
            'rol_sistema': forms.Select(attrs={
                'class':'form-select form-select-lg',
            },),
            'activo': forms.CheckboxInput(attrs={'class':'form-check-input lg-check-sena'}),
        }

    def __init__(self, *args, **kwargs):
        self.es_edicion = bool(kwargs.get('instance') and kwargs['instance'].pk)
        if self.es_edicion:
            kwargs.setdefault('initial', {})
        super().__init__(*args, **kwargs)
        # Campo de choices de rol — no usamos los labels del Modelo para que aparezcan con emoji primero
        self.fields['rol_sistema'].choices = self.ROLES_FORM
        self.fields['rol_sistema'].required = True
        # Al editar: el password NO es obligatorio. Ocultamos autogenerar por default, mostramos reset en botón aparte
        if self.es_edicion:
            self.fields['password_auto'].initial = False
            self.fields['password_auto'].label = '🔑 Resetear / Sobrescribir contraseña (la NUEVA se mostrará al guardar — CÓPIALA para dársela a la persona)'
            self.fields['password_manual'].required = False
            self.fields['password_manual'].label = 'Nueva contraseña (8 caracteres mín.) · Dejar vacío = generar automáticamente'

    def clean_username(self):
        v = (self.cleaned_data.get('username') or '').strip().lower()
        v = re.sub(r'[^a-z0-9\.\-\_]', '', v)
        if len(v) < 4:
            raise forms.ValidationError('❌ Usuario debe tener al menos 4 caracteres (letras/números).')
        if Usuario.objects.exclude(pk=self.instance.pk if self.instance.pk else None).filter(username=v).exists():
            raise forms.ValidationError('❌ Este usuario YA EXISTE — elige otro.')
        return v

    def clean_email(self):
        v = (self.cleaned_data.get('email') or '').strip().lower() or None
        if not v:
            raise forms.ValidationError('❌ El correo es obligatorio.')
        if Usuario.objects.exclude(pk=self.instance.pk if self.instance.pk else None).filter(email=v).exists():
            raise forms.ValidationError('❌ El correo electrónico ya está registrado en otro usuario.')
        return v

    def clean_nombres(self):
        v = (self.cleaned_data.get('nombres') or '').strip()
        v = re.sub(r'\s+', ' ', v)
        if len(v) < 3:
            raise forms.ValidationError('❌ Nombres deben tener mínimo 3 caracteres.')
        return v.upper()

    def clean_apellidos(self):
        v = (self.cleaned_data.get('apellidos') or '').strip()
        v = re.sub(r'\s+', ' ', v)
        if len(v) < 3:
            raise forms.ValidationError('❌ Apellidos deben tener mínimo 3 caracteres.')
        return v.upper()

    def clean(self):
        cleaned = super().clean()
        es_edicion = self.es_edicion
        pwd_auto = cleaned.get('password_auto')
        pwd_manual = (cleaned.get('password_manual') or '').strip()
        if not es_edicion:
            if pwd_auto:
                cleaned['_password_generada'] = generar_password_segura(10)
            else:
                if len(pwd_manual) < 8:
                    self.add_error('password_manual', '❌ Mínimo 8 caracteres para contraseña manual.')
                else:
                    cleaned['_password_generada'] = pwd_manual
        else:
            if pwd_auto:
                cleaned['_password_generada'] = generar_password_segura(10)
            elif pwd_manual:
                if len(pwd_manual) < 8:
                    self.add_error('password_manual', '❌ Mínimo 8 caracteres para nueva contraseña.')
                else:
                    cleaned['_password_generada'] = pwd_manual
            else:
                cleaned['_password_generada'] = None
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        # Sincronizar first_name / last_name con nombres/apellidos de AbstractUser
        user.first_name = user.nombres or ''
        user.last_name = user.apellidos or ''
        user.is_active = bool(user.activo)
        # Set password si aplica
        pwd = self.cleaned_data.get('_password_generada')
        if pwd:
            user.password = make_password(pwd)
        if commit:
            user.save()
            self.instance._password_generada = pwd
        return user


class ResetPasswordUsuarioForm(forms.Form):
    password_nueva = forms.CharField(
        label='Nueva contraseña (8+ caracteres)',
        required=False,
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'En blanco = generar automática',
            'autocomplete':'new-password',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        pwd = (cleaned.get('password_nueva') or '').strip()
        if not pwd:
            cleaned['_password_generada'] = generar_password_segura(12)
        elif len(pwd) < 8:
            raise forms.ValidationError('❌ La contraseña debe tener mínimo 8 caracteres.')
        else:
            cleaned['_password_generada'] = pwd
        return cleaned
