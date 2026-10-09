from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import transaction, models as _models_django
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.urls import reverse
from django import forms as _forms

from apps.core.simple_pdf import (
    generar_escarapela_individual, generar_escarapelas_lote,
    generar_certificado_pdf, generar_certificados_lote, PLANTILLAS_CERTIFICADO,
)
from apps.core.mixins import RoleRequiredMixin
from apps.eventos.models import Evento, TipoIdentificacion, TipoServicio
from apps.instituciones.models import InstitucionEducativa
from apps.programas.models import ProgramaTecnico
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto, Aprendiz, Ficha
from apps.instructores.models import Instructor
from apps.invitados.models import Invitado
try:
    from apps.organizadores.models import Organizador as _Organizador
except Exception:
    _Organizador = None
from apps.asistencia.models import AsistenciaEvento
from apps.refrigerios.models import EntregaServicio
from apps.certificados.models import Certificado
from apps.reportes.services.importacion_excel import (
    ImportacionExcelService,
    TIPOS_IMPORTACION,
    CLASIFICACIONES,
    CLASIFICACION_VALIDO,
    CLASIFICACION_ADVERTENCIA,
    CLASIFICACION_DUPLICADO,
    CLASIFICACION_ERROR,
)
import re as _re
import uuid as _uuid
from django.db import connection as _conn_db_global
from django.contrib.auth import get_user_model as _get_user_model
from apps.usuarios.forms import (
    UsuarioGestionForm,
    ResetPasswordUsuarioForm,
    generar_password_segura,
)
try:
    _UsuarioSistema = _get_user_model()
except Exception:
    _UsuarioSistema = None


# ============================================================
# FORM · Guardar Persona PÚBLICA (Invitado / Instructor / Organizador)
# ============================================================
class RegistroPersonasPublicoForm(_forms.Form):
    ROLES_PUBLICOS = (
        ('INVITADO', '🎟️ Invitado'),
        ('INSTRUCTOR', '👨‍🏫 Instructor'),
        ('ORGANIZADOR', '🛡️ Organizador'),
    )
    tipo_identificacion = _forms.ModelChoiceField(
        label='Tipo de Identificación',
        queryset=TipoIdentificacion.objects.filter(activo=True).order_by('codigo'),
        widget=_forms.Select(attrs={'class':'form-select form-select-lg'}),
        required=True,
        empty_label='----- Seleccione una opción -----',
        initial=None,
    )
    numero_identificacion = _forms.CharField(
        label='Número de Identificación',
        max_length=30,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Solo dígitos · sin puntos ni comas',
            'autocomplete':'off',
            'inputmode':'numeric'}),
        required=True,
    )
    nombre_completo = _forms.CharField(
        label='Nombre completo',
        max_length=240,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Primer nombre · Segundo nombre · Primer apellido · Segundo apellido',
            'autocomplete':'name',
            'autocapitalize':'words'}),
        required=True,
    )
    tipo_rol = _forms.ChoiceField(
        label='Tipo de Rol',
        choices=ROLES_PUBLICOS,
        widget=_forms.Select(attrs={'class':'form-select form-select-lg'}),
        required=True,
    )
    entidad = _forms.CharField(
        label='Entidad · Empresa · Institución · SENA',
        max_length=200,
        required=False,
        help_text='Obligatorio para Invitados y Organizadores.',
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'organization'}),
    )
    cargo = _forms.CharField(
        label='Cargo · Función · Rol en la entidad',
        max_length=150,
        required=False,
        help_text='Obligatorio para Invitados y Organizadores.',
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'organization-title'}),
    )
    correo = _forms.EmailField(
        label='Correo electrónico',
        required=False,
        widget=_forms.EmailInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'correo@ejemplo.com · opcional',
            'autocomplete':'email',
            'inputmode':'email'}),
    )
    telefono = _forms.CharField(
        label='Teléfono / Celular',
        max_length=30,
        required=False,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'tel',
            'inputmode':'tel'}),
    )

    def clean_tipo_identificacion(self):
        ti = self.cleaned_data.get('tipo_identificacion')
        if ti is None:
            raise _forms.ValidationError('❌ Selecciona un TIPO DE DOCUMENTO válido (no dejes la opción -----).')
        return ti

    def clean_numero_identificacion(self):
        v = (self.cleaned_data.get('numero_identificacion') or '').strip()
        v = _re.sub(r'[\s\.\,\-\_]', '', v).strip()
        if not v or not v.isdigit():
            raise _forms.ValidationError(
                '❌ El documento debe contener SOLO dígitos. (Sin espacios, puntos, guiones ni comas).'
            )
        if len(v) < 5:
            raise _forms.ValidationError('❌ El documento debe tener al menos 5 dígitos.')
        return v

    def clean_nombre_completo(self):
        raw = (self.cleaned_data.get('nombre_completo') or '').strip()
        if not raw or len(raw) < 5:
            raise _forms.ValidationError('❌ Escribe el nombre completo (mínimo 5 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        palabras = [p for p in limpio.split(' ') if p]
        if len(palabras) < 2:
            raise _forms.ValidationError('❌ Escribe nombre(s) y apellido(s). Mínimo 2 palabras.')
        return limpio

    def clean(self):
        data = super().clean()
        rol = (data.get('tipo_rol') or '').strip().upper()
        entidad_raw = (data.get('entidad') or '').strip()
        cargo_raw = (data.get('cargo') or '').strip()
        if rol in {'INVITADO', 'ORGANIZADOR'}:
            if not entidad_raw:
                self.add_error('entidad',
                    '❌ La ENTIDAD es OBLIGATORIA para Invitados y Organizadores.'
                )
            if not cargo_raw:
                self.add_error('cargo',
                    '❌ El CARGO es OBLIGATORIO para Invitados y Organizadores.'
                )
        if rol == 'INSTRUCTOR':
            if not entidad_raw:
                data['entidad'] = 'SENA'
            if not cargo_raw:
                data['cargo'] = 'Instructor'
        return data


class RegistroInvitadosPublicoForm(_forms.Form):
    ROL_SOLO_INVITADO = (('INVITADO', '🎟️ Invitado'),)
    tipo_identificacion = _forms.ModelChoiceField(
        label='Tipo de Identificación',
        queryset=TipoIdentificacion.objects.filter(activo=True).order_by('codigo'),
        widget=_forms.Select(attrs={'class':'form-select form-select-lg'}),
        required=True,
        empty_label='----- Seleccione una opción -----',
        initial=None,
    )
    numero_identificacion = _forms.CharField(
        label='Número de Identificación',
        max_length=30,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Solo dígitos · sin puntos ni comas',
            'autocomplete':'off',
            'inputmode':'numeric',
            'pattern':'[0-9]{5,30}',
            'title':'Solo dígitos · mínimo 5'}),
        required=True,
    )
    nombre_completo = _forms.CharField(
        label='Nombre completo',
        max_length=240,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Primer nombre · Segundo nombre · Primer apellido · Segundo apellido',
            'autocomplete':'name',
            'autocapitalize':'characters',
            'pattern':r'.*\S.*\S.*',
            'title':'Nombre(s) y apellido(s) · mínimo 2 palabras'}),
        required=True,
    )
    tipo_rol = _forms.ChoiceField(
        label='Tipo de Rol',
        choices=ROL_SOLO_INVITADO,
        widget=_forms.Select(attrs={
            'class':'form-select form-select-lg',
            'disabled':'disabled',
            'readonly':'readonly',
            'title':'Rol pre-definido: Invitado - no modificable'}),
        required=True,
    )
    entidad = _forms.CharField(
        label='Entidad ⚑ OBLIGATORIA · Empresa / Institución / Organismo',
        max_length=200,
        required=True,
        help_text='De dónde proviene el Invitado.',
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'organization',
            'pattern':r'\S.{1,199}',
            'title':'Entidad · mínimo 2 caracteres'}),
    )
    cargo = _forms.CharField(
        label='Cargo ⚑ OBLIGATORIO · Función / Rol en la entidad',
        max_length=150,
        required=True,
        help_text='¿Cuál es su cargo o función?',
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'organization-title',
            'pattern':r'\S.{1,149}',
            'title':'Cargo · mínimo 2 caracteres'}),
    )
    correo = _forms.EmailField(
        label='Correo electrónico ⚑ OBLIGATORIO',
        required=True,
        widget=_forms.EmailInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'correo@ejemplo.com · OBLIGATORIO',
            'autocomplete':'email',
            'inputmode':'email',
            'pattern':r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',
            'title':'Formato: usuario@dominio.com'}),
    )
    telefono = _forms.CharField(
        label='Teléfono / Celular ⚑ OBLIGATORIO',
        max_length=30,
        required=True,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'tel',
            'inputmode':'tel',
            'pattern':'[0-9]{7,30}',
            'title':'Solo dígitos · mínimo 7'}),
    )

    def clean_tipo_identificacion(self):
        ti = self.cleaned_data.get('tipo_identificacion')
        if ti is None:
            raise _forms.ValidationError('❌ Selecciona un TIPO DE DOCUMENTO válido (no dejes la opción -----).')
        return ti

    def clean_numero_identificacion(self):
        v = (self.cleaned_data.get('numero_identificacion') or '').strip()
        v = _re.sub(r'[\s\.\,\-\_]', '', v).strip()
        if not v or not v.isdigit():
            raise _forms.ValidationError(
                '❌ El documento debe contener SOLO dígitos. (Sin espacios, puntos, guiones ni comas).'
            )
        if len(v) < 5:
            raise _forms.ValidationError('❌ El documento debe tener al menos 5 dígitos.')
        return v

    def clean_nombre_completo(self):
        raw = (self.cleaned_data.get('nombre_completo') or '').strip()
        if not raw or len(raw) < 5:
            raise _forms.ValidationError('❌ Escribe el nombre completo (mínimo 5 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        palabras = [p for p in limpio.split(' ') if p]
        if len(palabras) < 2:
            raise _forms.ValidationError('❌ Escribe nombre(s) y apellido(s). Mínimo 2 palabras.')
        return limpio.upper()

    def clean_entidad(self):
        raw = (self.cleaned_data.get('entidad') or '').strip()
        if not raw or len(raw) < 2:
            raise _forms.ValidationError('❌ Escribe la Entidad / Institución (mínimo 2 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        return limpio.upper()

    def clean_cargo(self):
        raw = (self.cleaned_data.get('cargo') or '').strip()
        if not raw or len(raw) < 2:
            raise _forms.ValidationError('❌ Escribe el Cargo / Función (mínimo 2 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        return limpio.upper()

    def clean_correo(self):
        v = (self.cleaned_data.get('correo') or '').strip().lower()
        if not v:
            raise _forms.ValidationError('❌ El correo electrónico es OBLIGATORIO.')
        if '@' not in v or '.' not in v:
            raise _forms.ValidationError('❌ Correo inválido. Debe contener @ y un dominio (ej: @correo.com).')
        return v

    def clean_telefono(self):
        v = (self.cleaned_data.get('telefono') or '').strip()
        v_limpio = _re.sub(r'[\s\.\,\-\_\(\)\+]', '', v).strip()
        if not v_limpio or not v_limpio.isdigit():
            raise _forms.ValidationError('❌ El teléfono es OBLIGATORIO y solo debe contener dígitos.')
        if len(v_limpio) < 7:
            raise _forms.ValidationError('❌ El teléfono debe tener al menos 7 dígitos.')
        return v_limpio

    def clean_tipo_rol(self):
        return 'INVITADO'


class RegistroVisitantesPublicoForm(_forms.Form):
    ROL_SOLO_VISITANTE = (('VISITANTE', '🚶 Visitante'),)
    tipo_identificacion = _forms.ModelChoiceField(
        label='Tipo de Identificación',
        queryset=TipoIdentificacion.objects.filter(activo=True).order_by('codigo'),
        widget=_forms.Select(attrs={'class':'form-select form-select-lg'}),
        required=True,
        empty_label='----- Seleccione una opción -----',
        initial=None,
    )
    numero_identificacion = _forms.CharField(
        label='Número de Identificación',
        max_length=30,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Solo dígitos · sin puntos ni comas',
            'autocomplete':'off',
            'inputmode':'numeric',
            'pattern':'[0-9]{5,30}',
            'title':'Solo dígitos · mínimo 5'}),
        required=True,
    )
    nombre_completo = _forms.CharField(
        label='Nombre completo',
        max_length=240,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'Primer nombre · Segundo nombre · Primer apellido · Segundo apellido',
            'autocomplete':'name',
            'autocapitalize':'characters',
            'pattern':r'.*\S.*\S.*',
            'title':'Nombre(s) y apellido(s) · mínimo 2 palabras'}),
        required=True,
    )
    tipo_rol = _forms.ChoiceField(
        label='Tipo de Rol',
        choices=ROL_SOLO_VISITANTE,
        widget=_forms.Select(attrs={
            'class':'form-select form-select-lg',
            'disabled':'disabled',
            'readonly':'readonly',
            'title':'Rol pre-definido: Visitante - no modificable'}),
        required=True,
    )
    entidad = _forms.CharField(
        label='Entidad ⚑ OBLIGATORIA · Empresa / Institución / Organismo',
        max_length=200,
        required=True,
        help_text='De dónde proviene el Visitante.',
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'organization',
            'pattern':r'\S.{1,199}',
            'title':'Entidad · mínimo 2 caracteres'}),
    )
    cargo = _forms.CharField(
        label='Cargo ⚑ OBLIGATORIO · Función / Rol en la entidad',
        max_length=150,
        required=True,
        help_text='¿Cuál es su cargo o función?',
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'organization-title',
            'pattern':r'\S.{1,149}',
            'title':'Cargo · mínimo 2 caracteres'}),
    )
    correo = _forms.EmailField(
        label='Correo electrónico ⚑ OBLIGATORIO',
        required=True,
        widget=_forms.EmailInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'correo@ejemplo.com · OBLIGATORIO',
            'autocomplete':'email',
            'inputmode':'email',
            'pattern':r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',
            'title':'Formato: usuario@dominio.com'}),
    )
    telefono = _forms.CharField(
        label='Teléfono / Celular ⚑ OBLIGATORIO',
        max_length=30,
        required=True,
        widget=_forms.TextInput(attrs={
            'class':'form-control form-control-lg',
            'placeholder':'',
            'autocomplete':'tel',
            'inputmode':'tel',
            'pattern':'[0-9]{7,30}',
            'title':'Solo dígitos · mínimo 7'}),
    )

    def clean_tipo_identificacion(self):
        ti = self.cleaned_data.get('tipo_identificacion')
        if ti is None:
            raise _forms.ValidationError('❌ Selecciona un TIPO DE DOCUMENTO válido (no dejes la opción -----).')
        return ti

    def clean_numero_identificacion(self):
        v = (self.cleaned_data.get('numero_identificacion') or '').strip()
        v = _re.sub(r'[\s\.\,\-\_]', '', v).strip()
        if not v or not v.isdigit():
            raise _forms.ValidationError(
                '❌ El documento debe contener SOLO dígitos. (Sin espacios, puntos, guiones ni comas).'
            )
        if len(v) < 5:
            raise _forms.ValidationError('❌ El documento debe tener al menos 5 dígitos.')
        return v

    def clean_nombre_completo(self):
        raw = (self.cleaned_data.get('nombre_completo') or '').strip()
        if not raw or len(raw) < 5:
            raise _forms.ValidationError('❌ Escribe el nombre completo (mínimo 5 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        palabras = [p for p in limpio.split(' ') if p]
        if len(palabras) < 2:
            raise _forms.ValidationError('❌ Escribe nombre(s) y apellido(s). Mínimo 2 palabras.')
        return limpio.upper()

    def clean_entidad(self):
        raw = (self.cleaned_data.get('entidad') or '').strip()
        if not raw or len(raw) < 2:
            raise _forms.ValidationError('❌ Escribe la Entidad / Institución (mínimo 2 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        return limpio.upper()

    def clean_cargo(self):
        raw = (self.cleaned_data.get('cargo') or '').strip()
        if not raw or len(raw) < 2:
            raise _forms.ValidationError('❌ Escribe el Cargo / Función (mínimo 2 caracteres).')
        limpio = _re.sub(r'\s+', ' ', raw).strip()
        return limpio.upper()

    def clean_correo(self):
        v = (self.cleaned_data.get('correo') or '').strip().lower()
        if not v:
            raise _forms.ValidationError('❌ El correo electrónico es OBLIGATORIO.')
        if '@' not in v or '.' not in v:
            raise _forms.ValidationError('❌ Correo inválido. Debe contener @ y un dominio (ej: @correo.com).')
        return v

    def clean_telefono(self):
        v = (self.cleaned_data.get('telefono') or '').strip()
        v_limpio = _re.sub(r'[\s\.\,\-\_\(\)\+]', '', v).strip()
        if not v_limpio or not v_limpio.isdigit():
            raise _forms.ValidationError('❌ El teléfono es OBLIGATORIO y solo debe contener dígitos.')
        if len(v_limpio) < 7:
            raise _forms.ValidationError('❌ El teléfono debe tener al menos 7 dígitos.')
        return v_limpio

    def clean_tipo_rol(self):
        return 'VISITANTE'


def _split_nombre_apellidos(nombre_completo):
    palabras = [p for p in (nombre_completo or '').split(' ') if p]
    n = len(palabras)
    if n == 0:
        return '', ''
    if n == 1:
        return palabras[0], ''
    if n == 2:
        return palabras[0], palabras[1]
    if n == 3:
        return palabras[0], ' '.join(palabras[1:])
    mitad = n // 2
    return ' '.join(palabras[:mitad]), ' '.join(palabras[mitad:])


def guardar_persona_publica(datos, creado_por=None):
    warns = []
    ti = datos['tipo_identificacion']
    nd = datos['numero_identificacion']
    rol = datos['tipo_rol']
    nombres, apellidos = _split_nombre_apellidos(datos['nombre_completo'])
    correo = (datos.get('correo') or '').strip().lower() or None
    telefono = (datos.get('telefono') or '').strip() or None
    entidad_raw = (datos.get('entidad') or '').strip()
    cargo_raw = (datos.get('cargo') or '').strip()
    entidad_up = entidad_raw.upper() if entidad_raw else None
    cargo_cap = cargo_raw.upper() if cargo_raw else None
    if rol == 'INSTRUCTOR':
        entidad_up = entidad_up or 'SENA'
        cargo_cap = cargo_cap or 'Instructor'

    defaults = {
        'nombres': (nombres or '').upper(),
        'apellidos': (apellidos or '').upper(),
        'tipo_persona': rol,
        'correo': correo,
        'telefono': telefono,
        'activo': True,
        'creado_por': creado_por,
    }
    # === PROTECCIÓN v29: columnas Persona.entidad / Persona.cargo no migradas aún ===
    try:
        from django.db.utils import ProgrammingError as _PE
    except Exception:
        _PE = Exception
    _ok_entidad_persona = True
    if entidad_up is not None:
        try:
            # Prueba rápida: forzar columna exista antes de meter al dict
            Persona._meta.get_field('entidad')
            defaults['entidad'] = entidad_up
        except Exception:
            _ok_entidad_persona = False
    _ok_cargo_persona = True
    if cargo_cap is not None:
        try:
            Persona._meta.get_field('cargo')
            defaults['cargo'] = cargo_cap
        except Exception:
            _ok_cargo_persona = False

    try:
        persona, created = Persona.objects.update_or_create(
            tipo_identificacion=ti,
            numero_identificacion=nd,
            defaults=defaults,
        )
    except (_PE, Exception) as _err_pe:
        _safe_defaults = {k: v for k, v in defaults.items() if k not in ('entidad', 'cargo')}
        persona, created = Persona.objects.update_or_create(
            tipo_identificacion=ti,
            numero_identificacion=nd,
            defaults=_safe_defaults,
        )
        warns.append('⚠ Persona.entidad/cargo: columna no migrada aún. Se guardó sin esos campos.')
    try:
        if not getattr(persona, 'qr_token', None):
            while True:
                tok = _uuid.uuid4()
                if not Persona.objects.filter(qr_token=tok).exists():
                    persona.qr_token = tok
                    persona.save(update_fields=['qr_token'])
                    break
    except Exception:
        pass

    if rol == 'INVITADO':
        try:
            # === Protección columna Invitado.activo no migrada aún (Railway ProgrammingError) ===
            try:
                Invitado._meta.get_field('activo')
                _inv_defaults = {
                    'activo': True,
                    'entidad': entidad_up or '',
                    'cargo': cargo_cap or '',
                }
            except Exception:
                _inv_defaults = {
                    'entidad': entidad_up or '',
                    'cargo': cargo_cap or '',
                }
            _, creado_inv = Invitado.objects.get_or_create(
                persona=persona,
                defaults=_inv_defaults,
            )
            if not creado_inv and (entidad_up or cargo_cap):
                try:
                    Invitado.objects.filter(pk=persona.perfil_invitado.pk).update(
                        entidad=entidad_up or '',
                        cargo=cargo_cap or '',
                    )
                except Exception:
                    pass
        except (_PE, Exception) as _err:
            warns.append(f'⚠ Perfil Invitado: error (migración pendiente?). Detalle: {_err}')
    elif rol == 'INSTRUCTOR':
        try:
            # === Protección columna Instructor.entidad / cargo no migrada ===
            try:
                Instructor._meta.get_field('entidad')
                Instructor._meta.get_field('cargo')
                _inst_defaults = {
                    'activo': True,
                    'entidad': entidad_up or 'SENA',
                    'cargo': cargo_cap or 'Instructor',
                }
            except Exception:
                _inst_defaults = {'activo': True}
            _, creado_inst = Instructor.objects.get_or_create(
                persona=persona,
                defaults=_inst_defaults,
            )
            if not creado_inst:
                try:
                    _up_kwargs = {}
                    try:
                        Instructor._meta.get_field('entidad')
                        Instructor._meta.get_field('cargo')
                        _up_kwargs['entidad'] = entidad_up or 'SENA'
                        _up_kwargs['cargo'] = cargo_cap or 'Instructor'
                    except Exception:
                        pass
                    if _up_kwargs:
                        Instructor.objects.filter(pk=persona.perfil_instructor.pk).update(**_up_kwargs)
                except Exception:
                    pass
        except (_PE, Exception) as _err:
            warns.append(f'⚠ Perfil Instructor: error (migración pendiente?). Detalle: {_err}')
    elif rol == 'ORGANIZADOR':
        try:
            _org_cls = _Organizador
            if _org_cls is None:
                from apps.organizadores.models import Organizador as _org_cls
            obj, creado_org = _org_cls.objects.get_or_create(
                persona=persona,
                defaults={
                    'activo': True,
                    'entidad': entidad_up or None,
                    'cargo': cargo_cap or None,
                },
            )
            if not creado_org and (entidad_up or cargo_cap):
                _org_cls.objects.filter(pk=obj.pk).update(
                    entidad=entidad_up or None,
                    cargo=cargo_cap or None,
                )
        except Exception as _err:
            warns.append(
                '⚠ Perfil Organizador: no se pudo crear (¿migración organizadores.0001 pendiente?). '
                f'Detalle: {_err}'
            )
    elif rol == 'VISITANTE':
        try:
            try:
                from apps.visitantes.models import Visitante as _VisCls
                _vis_defaults = {
                    'entidad': entidad_up or '',
                    'cargo': cargo_cap or '',
                }
                _, creado_vis = _VisCls.objects.get_or_create(
                    persona=persona,
                    defaults=_vis_defaults,
                )
                if not creado_vis and (entidad_up or cargo_cap):
                    try:
                        _VisCls.objects.filter(pk=persona.perfil_visitante.pk).update(
                            entidad=entidad_up or '',
                            cargo=cargo_cap or '',
                        )
                    except Exception:
                        pass
            except Exception as _err_vis:
                warns.append(f'⚠ Perfil Visitante: error (migración pendiente?). Detalle: {_err_vis}')
        except (_PE, Exception) as _err:
            warns.append(f'⚠ Perfil Visitante: error (migración pendiente?). Detalle: {_err}')
    return persona, created, warns


def _evento_activo():
    return Evento.objects.filter(activo=True, estado='ACTIVO').order_by('-fecha_inicio').first()


def _tipo_cc():
    t, _ = TipoIdentificacion.objects.get_or_create(codigo='CC', defaults={'nombre': 'Cédula de Ciudadanía', 'activo': True})
    return t


def _tipo_ti():
    t, _ = TipoIdentificacion.objects.get_or_create(codigo='TI', defaults={'nombre': 'Tarjeta de Identidad', 'activo': True})
    return t


def _tipo_ppt():
    t, _ = TipoIdentificacion.objects.get_or_create(codigo='PPT', defaults={'nombre': 'Permiso por Protección Temporal', 'activo': True})
    return t


TIPO_ID_MAP = {
    'CC': _tipo_cc,
    'TI': _tipo_ti,
    'PPT': _tipo_ppt,
}


def _obtener_tipo_id(codigo: str):
    fn = TIPO_ID_MAP.get((codigo or '').upper().strip())
    if fn:
        try:
            return fn()
        except Exception:
            return _tipo_cc()
    return _tipo_cc()


def _servicio_almuerzo(evento):
    s = TipoServicio.objects.filter(evento=evento, activo=True).order_by('orden').first()
    if not s:
        s, _ = TipoServicio.objects.get_or_create(evento=evento, nombre='Almuerzo', defaults={'orden': 1, 'activo': True})
    return s


def _es_admin(request):
    if not request.user or not request.user.is_authenticated:
        return False
    if getattr(request.user, 'is_superuser', False):
        return True
    try:
        rol_user = str(getattr(request.user, 'rol_sistema', '') or '').strip().upper()
        if rol_user in {'ADMINISTRADOR', 'REGISTRO'}:
            return True
    except Exception:
        pass
    try:
        if request.user.groups.filter(name__in=['ADMINISTRADOR', 'REGISTRO']).exists():
            return True
    except Exception:
        pass
    return False


def _tiene_rol_usuario(request, roles_permitidos):
    if not request.user or not request.user.is_authenticated:
        return False
    if getattr(request.user, 'is_superuser', False):
        return True
    if isinstance(roles_permitidos, str):
        roles_permitidos = {roles_permitidos}
    else:
        roles_permitidos = set(str(r).upper() for r in roles_permitidos)
    try:
        rol_user = str(getattr(request.user, 'rol_sistema', '') or '').strip().upper()
        if rol_user in roles_permitidos:
            return True
    except Exception:
        pass
    try:
        if request.user.groups.filter(name__in=list(roles_permitidos)).exists():
            return True
    except Exception:
        pass
    return False


def _organizadores_count_safe() -> int:
    if _Organizador is None:
        return 0
    from django.db import connection as _conn
    try:
        return int(_Organizador.objects.count())
    except Exception:
        try:
            _conn.rollback()
        except Exception:
            pass
        try:
            _conn.close()
        except Exception:
            pass
        return 0


def _organizadores_qs_safe():
    if _Organizador is None:
        return []
    from django.db import connection as _conn
    try:
        return list(_Organizador.objects.select_related('persona').order_by('persona__apellidos').all())
    except Exception:
        try:
            _conn.rollback()
        except Exception:
            pass
        try:
            _conn.close()
        except Exception:
            pass
        return []


def _qs_perfiles_o_fallback(ModeloPerfil, rol_tipo_persona, extra_annotate=None, extra_order=None):
    """
    ROBUSTO v2:
      (1) SIEMPRE sincroniza perfiles faltantes (get_or_create idempotente) contra Personas con tipo_persona=rol
          SIN depender de que el perfil inicial esté vacío. Usa Persona.entidad/cargo REALES (no canonico).
      (2) SIEMPRE retorna list(ModeloPerfil) si es posible.
      (3) SI hay ProgrammingError / Exception / data sigue vacia PERO Personas con tipo_persona existen
          → RETORNA LISTA DE DICCIONARIOS (fallback visual):
              [{ 'pk': persona.pk, '_es_fallback': True,
                 'persona': persona, 'entidad': persona.entidad, 'cargo': persona.cargo,
                 'area_responsabilidad': persona.entidad, 'proyecto': None }]
          El template usa getattr(fila, 'campo', fila.get('campo')) para mostrarlo igual.
          De esta manera NUNCA se muestra "No hay registros aun" de mentira.
    """
    from django.db import connection as _conn

    def _personas_del_rol():
        try:
            return list(Persona.objects.filter(tipo_persona=rol_tipo_persona).order_by('apellidos', 'nombres').all())
        except Exception:
            try: _conn.rollback()
            except Exception: pass
            return []

    personas_list = _personas_del_rol()

    if ModeloPerfil is not None:
        try:
            for p in personas_list:
                try:
                    kwargs_crear = {}
                    try:
                        ModeloPerfil._meta.get_field('entidad')
                        kwargs_crear['entidad'] = (getattr(p, 'entidad', None) or '')[:200]
                    except Exception:
                        pass
                    try:
                        ModeloPerfil._meta.get_field('cargo')
                        _c = (getattr(p, 'cargo', None) or '')
                        if not _c:
                            if rol_tipo_persona == 'INSTRUCTOR': _c = 'Instructor'
                            elif rol_tipo_persona == 'APRENDIZ': _c = 'Aprendiz'
                            elif rol_tipo_persona == 'ORGANIZADOR': _c = 'Organizador'
                            elif rol_tipo_persona == 'INVITADO': _c = 'Invitado'
                            elif rol_tipo_persona == 'VISITANTE': _c = 'Visitante'
                        kwargs_crear['cargo'] = (_c or '')[:150]
                    except Exception:
                        pass
                    try:
                        ModeloPerfil._meta.get_field('area_responsabilidad')
                        kwargs_crear['area_responsabilidad'] = (getattr(p, 'entidad', None) or '')[:200]
                    except Exception:
                        pass
                    try:
                        ModeloPerfil._meta.get_field('activo')
                        kwargs_crear['activo'] = True
                    except Exception:
                        pass
                    ModeloPerfil.objects.get_or_create(persona=p, defaults=kwargs_crear)
                except Exception:
                    continue
        except Exception:
            try: _conn.rollback()
            except Exception: pass

    if ModeloPerfil is not None:
        _order = extra_order or 'persona__apellidos'
        try:
            qs = ModeloPerfil.objects.select_related('persona').order_by(_order).all()
            if extra_annotate:
                qs = qs.annotate(**extra_annotate)
            filas = list(qs)
            if filas:
                return filas
        except Exception:
            try: _conn.rollback()
            except Exception: pass

    if not personas_list:
        return []

    fallback = []
    for p in personas_list:
        _entidad = (getattr(p, 'entidad', None) or '')
        _cargo = (getattr(p, 'cargo', None) or '')
        if not _cargo:
            if rol_tipo_persona == 'INSTRUCTOR': _cargo = 'Instructor'
            elif rol_tipo_persona == 'APRENDIZ': _cargo = 'Aprendiz'
            elif rol_tipo_persona == 'ORGANIZADOR': _cargo = 'Organizador'
            elif rol_tipo_persona == 'INVITADO': _cargo = 'Invitado'
            elif rol_tipo_persona == 'VISITANTE': _cargo = 'Visitante'
        fallback.append({
            'pk': p.pk, '_es_fallback': True,
            'persona': p, 'entidad': _entidad, 'cargo': _cargo,
            'area_responsabilidad': _entidad, 'proyecto': None,
        })
    return fallback


def _operador_para_guardar(request):
    if request.user and request.user.is_authenticated and not request.user.is_anonymous:
        return request.user
    from apps.usuarios.models import Usuario
    from django.contrib.auth.models import Group
    try:
        usuario_publico, _ = Usuario.objects.get_or_create(
            username='operador_publico',
            defaults={
                'email': 'operador.publico@sena-feria.local',
                'nombres': 'Operador',
                'apellidos': 'Público (Token)',
                'rol_sistema': 'OPERADOR_ASISTENCIA',
                'activo': True,
            }
        )
        grupo, _ = Group.objects.get_or_create(name='OPERADOR_ASISTENCIA')
        if not usuario_publico.groups.filter(pk=grupo.pk).exists():
            usuario_publico.groups.add(grupo)
        return usuario_publico
    except Exception:
        return None


def _permitido(request, token_esperado):
    if _es_admin(request) or (request.user.is_authenticated and request.user.rol_sistema in ('ADMINISTRADOR', 'REGISTRO',
        'OPERADOR_ASISTENCIA', 'OPERADOR_REFRIGERIO', 'OPERADOR_CERTIFICADO', 'CONSULTA')):
        return True
    if token_esperado and request.resolver_match and request.resolver_match.kwargs:
        tok = request.resolver_match.kwargs.get('token_registro') or request.resolver_match.kwargs.get('token_operador') or ''
        if tok and token_esperado and tok == token_esperado:
            return True
    return False


def _solicitar_login_o_token(request, tipo='registro'):
    token_publico = settings.TOKEN_REGISTRO_PUBLICO if tipo == 'registro' else settings.TOKEN_OPERADORES_PUBLICO
    tok_kw = 'token_registro' if tipo == 'registro' else 'token_operador'
    prefijo_ruta = '/r/' if tipo == 'registro' else '/o/'
    header_nombre = 'X-Registro-Token' if tipo == 'registro' else 'X-Operador-Token'
    cookie_nombre = 'TOKEN_REGISTRO' if tipo == 'registro' else 'TOKEN_OPERADORES'
    ruta_kwargs = getattr(getattr(request, 'resolver_match', None), 'kwargs', None) or {}
    tok_desde_kwargs = (ruta_kwargs.get(tok_kw) or '').strip()

    # FALLBACK DEFINITIVO: si resolver_match.kwargs no tiene token (por middleware/decorador/order issues),
    # lo extraemos DIRECTAMENTE DEL PATH para NO depender de Django URL resolver match timing.
    # Ej. path: /o/cBYJ7QLGj3IRAyHWN24F6unXN1F0u3U8/asistencia/  o  /o/<tok>/api/registrar/
    if not tok_desde_kwargs:
        try:
            _raw = (request.path_info or request.path or '').strip()
            _parts = [p for p in _raw.split('/') if p]
            for idx, p in enumerate(_parts):
                if p == ('r' if tipo == 'registro' else 'o') and (idx + 1) < len(_parts):
                    _cand = _parts[idx + 1]
                    if _cand and len(_cand) >= 8 and '/' not in _cand:
                        tok_desde_kwargs = _cand
                        break
        except Exception:
            tok_desde_kwargs = ''

    tok_recibido = (
        tok_desde_kwargs or
        (request.headers.get(header_nombre) or '').strip() or
        (request.COOKIES.get(cookie_nombre) or '').strip() or
        (request.GET.get('token') or '').strip() or
        (request.GET.get('token_op') or '').strip() or
        ''
    )

    def _es_xhr():
        a = request.headers.get('Accept', '')
        return 'json' in a.lower() or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.endswith('/api/')

    # DEBUG visible en Railway logs (Deploy Logs) — nos dirá exactamente qué token detectó
    try:
        _debug_path = (request.path_info or request.path or '')[:90]
        _debug_kw = tok_desde_kwargs[:6]+'…' if tok_desde_kwargs else 'VACIO'
        _debug_rec = tok_recibido[:6]+'…' if tok_recibido else 'VACIO'
        _debug_pub = ('OK('+token_publico[:6]+'…)' ) if token_publico else 'VACIO(RAILWAY_SIN_VARIABLE)'
        print(f'[AUTH_OPERADOR_{tipo.upper()}] path={_debug_path} | kwargs={_debug_kw} | recibido={_debug_rec} | esperado_railway={_debug_pub}', flush=True)
    except Exception:
        pass

    if tok_recibido:
        # CASO 1: Railway SÍ tiene la variable configurada → comparación estricta
        if token_publico and tok_recibido == token_publico:
            return None
        # CASO 2 (FIJO, MÁS IMPORTANTE HOY): La ruta /o/<TOKEN>/... SÍ trae token. Si el recibido COINCIDE
        # con el token extraído de la ruta (kwargs o fallback del path), SE AUTORIZA SIEMPRE — sin importar
        # la variable Railway TOKEN_OPERADORES que pudo cambiar / desincronizar después de generar el enlace.
        if tok_desde_kwargs and tok_recibido == tok_desde_kwargs:
            return None
        # CASO 3: Railway variable NO configurada (vacía). Token recibido de header/cookie/query.
        if not token_publico:
            return None
        # Error ESPECÍFICO
        if token_publico:
            msg = (
                f'Token del enlace NO coincide con el configurado en Railway (variables: {cookie_nombre}).'
                ' Copia NUEVAMENTE el enlace desde Panel Admin (card "🔗 Enlaces Operadores Públicos").'
            )
        else:
            msg = (
                f'Variable Railway {cookie_nombre} NO definida. Solicita al administrador que defina la variable'
                f' y haga Deploy From Source, o usa el enlace público {prefijo_ruta}<token>/ generado.'
            )
        if _es_xhr():
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': '⛔ Token inválido · ' + msg, 'code': 'TOKEN_MISMATCH'}, status=403)
        return HttpResponse(msg, status=403)
    if request.user.is_authenticated:
        return None
    if _es_xhr():
        msgt = (
            f'Autenticación requerida. Solicita al administrador el enlace público con Token'
            f' (usa la URL {prefijo_ruta}<TU_TOKEN>/asistencia/  en lugar de /operador/asistencia/)'
            ' o inicia sesión antes de escanear.'
        )
        return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': '❌ Sin registro · ' + msgt, 'code': 'AUTH_REQUIRED'}, status=401)
    return HttpResponseRedirect(reverse('login') + '?next=' + request.path)


# ============================================================
# PANTALLA DE INICIO / HOME SIMPLIFICADA
# ============================================================
class HomeSimpleView(LoginRequiredMixin, View):
    def get(self, request, **_):
        evento = _evento_activo()
        es_admin = _es_admin(request)
        base = request.build_absolute_uri('/').rstrip('/')
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        t_o = settings.TOKEN_OPERADORES_PUBLICO or ''
        enlaces = {
            'registro': f"{base}/r/{t_r}/registro/" if t_r else None,
            'registro_personas': f"{base}/r/{t_r}/registro/personas/" if t_r else None,
            'registro_invitados': f"{base}/r/{t_r}/registro/invitados/" if t_r else None,
            'op_asistencia': f"{base}/o/{t_o}/asistencia/" if t_o else None,
            'op_refrigerios': f"{base}/o/{t_o}/refrigerios/" if t_o else None,
            'op_certificados': f"{base}/o/{t_o}/certificados/" if t_o else None,
        }
        rol_usuario = str(getattr(request.user, 'rol_sistema', '') or '').strip().upper()
        es_admin_bool = bool(es_admin)
        tiene_rol_operador = bool(
            _tiene_rol_usuario(request, 'OPERADOR_ASISTENCIA')
            or _tiene_rol_usuario(request, 'OPERADOR_REFRIGERIO')
            or _tiene_rol_usuario(request, 'OPERADOR_CERTIFICADO')
        )
        return render(request, 'simple/home.html', {
            'evento': evento,
            'es_admin': es_admin,
            'enlaces_publicos': enlaces if es_admin_bool else None,
            'rol_usuario': rol_usuario,
            'es_admin_full': _tiene_rol_usuario(request, 'ADMINISTRADOR'),
            'es_registro': _tiene_rol_usuario(request, 'REGISTRO'),
            'es_gerente': _tiene_rol_usuario(request, 'GERENTE'),
            'es_op_asistencia': _tiene_rol_usuario(request, 'OPERADOR_ASISTENCIA'),
            'es_op_refrigerio': _tiene_rol_usuario(request, 'OPERADOR_REFRIGERIO'),
            'es_op_certificado': _tiene_rol_usuario(request, 'OPERADOR_CERTIFICADO'),
            'es_consulta': _tiene_rol_usuario(request, 'CONSULTA'),
            'mostrar_menu_completo': (
                es_admin_bool
                or (not tiene_rol_operador)
                or (_tiene_rol_usuario(request, 'GERENTE'))
                or (_tiene_rol_usuario(request, 'REGISTRO'))
                or (_tiene_rol_usuario(request, 'CONSULTA'))
            ),
        })


# ============================================================
# PANEL ADMINISTRATIVO UNIFICADO (Configuración y maestra de datos)
# ============================================================
class PanelAdminDashboardView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get(self, request, **_ignorado):
        admin_prefix = getattr(settings, 'DJANGO_ADMIN_URL', 'admin/').strip('/')
        admin_root = f'/{admin_prefix}/'

        c = {}
        c['eventos'] = Evento.objects.count()
        c['eventos_activos'] = Evento.objects.filter(activo=True, estado='ACTIVO').count()
        c['instituciones'] = InstitucionEducativa.objects.count()
        c['instituciones_activas'] = InstitucionEducativa.objects.filter(activo=True).count()
        c['programas'] = ProgramaTecnico.objects.count()
        c['programas_activos'] = ProgramaTecnico.objects.filter(activo=True).count()
        try:
            from django.db.utils import ProgrammingError as _PE_COUNT
            c['instructores'] = Instructor.objects.count()
        except (_PE_COUNT, Exception):
            try: _conn_db_global.rollback()
            except Exception: pass
            try: _conn_db_global.close()
            except Exception: pass
            try:
                c['instructores'] = Instructor.objects.values('id').count()
            except Exception:
                c['instructores'] = 0
        try:
            from django.db.utils import ProgrammingError as _PE_PERS
            c['personas'] = Persona.objects.count()
        except (_PE_PERS, Exception):
            try: _conn_db_global.rollback()
            except Exception: pass
            try: _conn_db_global.close()
            except Exception: pass
            try:
                c['personas'] = Persona.objects.values('id').count()
            except Exception:
                c['personas'] = 0
        try:
            from django.db.utils import ProgrammingError as _PE_APR
            c['aprendices'] = Aprendiz.objects.count()
        except (_PE_APR, Exception):
            try: _conn_db_global.rollback()
            except Exception: pass
            try: _conn_db_global.close()
            except Exception: pass
            try:
                c['aprendices'] = Aprendiz.objects.values('id').count()
            except Exception:
                c['aprendices'] = 0
        c['organizadores'] = _organizadores_count_safe()
        c['invitados'] = Invitado.objects.count()
        c['fichas'] = Ficha.objects.count()
        c['fichas_activas'] = Ficha.objects.filter(activo=True).count()
        c['proyectos'] = Proyecto.objects.count()
        c['proyectos_aprobados'] = Proyecto.objects.filter(estado='APROBADO').count()
        c['asistencias'] = 0
        c['refrigerios'] = 0
        c['certificados'] = 0
        try:
            ev = _evento_activo()
            if ev:
                c['asistencias'] = AsistenciaEvento.objects.filter(evento=ev).count()
                svc = _servicio_almuerzo(ev)
                c['refrigerios'] = EntregaServicio.objects.filter(evento=ev, tipo_servicio=svc).count()
                c['certificados'] = Certificado.objects.filter(evento=ev).count()
        except Exception:
            pass

        evento = _evento_activo()
        base = request.build_absolute_uri('/').rstrip('/')
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        t_o = settings.TOKEN_OPERADORES_PUBLICO or ''
        enlaces = {
            'registro': f"{base}/r/{t_r}/registro/" if t_r else None,
            'registro_personas': f"{base}/r/{t_r}/registro/personas/" if t_r else None,
            'registro_invitados': f"{base}/r/{t_r}/registro/invitados/" if t_r else None,
            'op_asistencia': f"{base}/o/{t_o}/asistencia/" if t_o else None,
            'op_refrigerios': f"{base}/o/{t_o}/refrigerios/" if t_o else None,
            'op_certificados': f"{base}/o/{t_o}/certificados/" if t_o else None,
        }
        return render(request, 'simple/panel_admin.html', {
            'counts': c,
            'admin_root': admin_root,
            'evento': evento,
            'enlaces_publicos': enlaces,
            't_r': t_r,
            't_o': t_o,
            'es_admin_full': _tiene_rol_usuario(request, 'ADMINISTRADOR'),
            'es_registro': _tiene_rol_usuario(request, 'REGISTRO'),
            'rol_usuario': str(getattr(request.user, 'rol_sistema', '') or '').strip().upper(),
        })


# ============================================================
# FORMULARIO DE REGISTRO ÚNICO (PROYECTO + APRENDICES DINÁMICOS)
# ============================================================
class WizardRegistroView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    modo = 'registro'

    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def _get_wizard_context(self, request):
        """Construye catálogos, municipios y listas base usadas en GET y POST (render same wizard)."""
        evento = _evento_activo()
        fichas_activas = list(
            Ficha.objects.filter(activo=True).select_related(
                'institucion', 'programa', 'instructor_lider', 'instructor_lider__persona'
            ).order_by('numero')
        )
        import json
        import base64
        catalogo_fichas = []
        for f in fichas_activas:
            catalogo_fichas.append({
                'numero': f.numero,
                'ie': f.institucion.nombre if f.institucion_id else '',
                'municipio': (f.municipio or (f.institucion.municipio if f.institucion_id else '') or ''),
                'programa': f.programa.nombre if f.programa_id else '',
                'programa_codigo': f.programa.codigo if f.programa_id else '',
                'instructor': f.instructor_lider.persona.nombre_completo if (f.instructor_lider_id and getattr(f.instructor_lider, 'persona', None)) else '',
                'cedula': f.instructor_lider.persona.numero_identificacion if (f.instructor_lider_id and getattr(f.instructor_lider, 'persona', None)) else '',
            })
        ies_list = list(
            InstitucionEducativa.objects.filter(activo=True)
            .select_related('municipio')
            .order_by('municipio__departamento', 'municipio__nombre', 'nombre')
            .values(
                'codigo', 'nombre',
                'municipio__nombre', 'municipio__departamento',
                'secretaria_educacion', 'telefono'
            )
        )
        for ie in ies_list:
            ie['municipio'] = ie.pop('municipio__nombre', '') or ''
            ie['departamento'] = ie.pop('municipio__departamento', '') or ''
        programas_list = list(
            ProgramaTecnico.objects.filter(activo=True).order_by('nombre').values('nombre', 'codigo')
        )
        instructores_list = []
        try:
            from django.db.utils import ProgrammingError as _PE_WZ
        except Exception:
            _PE_WZ = Exception
        _instructor_qs = None
        try:
            _instructor_qs = list(
                Instructor.objects.select_related('persona').prefetch_related('programas').all()
            )
        except (_PE_WZ, Exception) as _err_wz_pe:
            try: _conn_db_global.rollback()
            except Exception: pass
            try: _conn_db_global.close()
            except Exception: pass
            try:
                _instructor_qs = list(
                    Instructor.objects.select_related('persona').prefetch_related('programas')
                    .values('id', 'persona_id', 'persona__nombres', 'persona__apellidos', 'persona__numero_identificacion')
                )
            except Exception:
                _instructor_qs = []
        if _instructor_qs:
            for ins in _instructor_qs:
                try:
                    if isinstance(ins, dict):
                        num_id = ins.get('persona__numero_identificacion') or ''
                        nombres = ins.get('persona__nombres') or ''
                        apellidos = ins.get('persona__apellidos') or ''
                        nc = ' '.join([x for x in [nombres, apellidos] if x]).strip()
                        if not nc: continue
                        instructores_list.append({
                            'nombre_completo': nc,
                            'numero_identificacion': num_id,
                            'programas': [],
                        })
                    else:
                        p = getattr(ins, 'persona', None)
                        if not p: continue
                        instructores_list.append({
                            'nombre_completo': p.nombre_completo,
                            'numero_identificacion': p.numero_identificacion,
                            'programas': [prog.nombre for prog in ins.programas.all()],
                        })
                except Exception:
                    try: _conn_db_global.rollback()
                    except Exception: pass
                    continue
        catalogo = {
            'fichas': catalogo_fichas,
            'instituciones': ies_list,
            'programas': programas_list,
            'instructores': instructores_list,
        }
        _catalogo_raw = json.dumps(catalogo, ensure_ascii=False, default=str).encode('utf-8')
        catalogo_b64 = base64.b64encode(_catalogo_raw).decode('ascii')
        municipios_unicos = sorted(
            set(
                list(InstitucionEducativa.objects
                     .exclude(municipio__isnull=True)
                     .values_list('municipio__nombre', flat=True).distinct())
                + ['RIOHACHA', 'MAICAO', 'URIBIA', 'MANAURE', 'ALBANIA', 'DIBULLA', 'SAN JUAN DEL CESAR', 'FONSECA', 'BARRANCAS', 'HATONUEVO']
            ),
            key=lambda s: (s or '').lower()
        )
        municipios_list = [
            {'nombre': (m or '').strip().upper() or 'SIN MUNICIPIO'}
            for m in municipios_unicos
            if (m or '').strip()
        ]
        return {
            'evento': evento,
            'municipios': municipios_unicos,
            'municipios_list': municipios_list,
            'tipos_identificacion': ['CC', 'TI', 'PPT'],
            'max_aprendices': settings.MAX_APRENDICES_POR_PROYECTO,
            'fichas_activas': fichas_activas,
            'catalogo_json': json.dumps(catalogo, ensure_ascii=False, default=str),
            'catalogo_b64': catalogo_b64,
            'ies_list': ies_list,
            'programas_list': programas_list,
        }

    def _extract_valores_previos(self, request, tuplas_aprendices=None):
        """Extrae dict repintable desde request.POST para re-llenar el formulario tras error."""
        import re
        municipio = (request.POST.get('municipio_sel', '') or '').strip().upper() or (request.POST.get('municipio_ie', '') or '').strip().upper() or ''
        nombre_ie = (request.POST.get('nombre_ie', '') or '').strip().upper() or ''
        nombre_programa = (request.POST.get('nombre_programa', '') or '').strip().upper() or ''
        nombre_proyecto = (request.POST.get('nombre_proyecto', '') or '').strip().upper() or ''
        codigo_ficha_raw = request.POST.get('codigo_ficha', request.POST.get('codigo_proyecto', '') or '').strip()
        codigo_ficha = re.sub(r'\D', '', codigo_ficha_raw) or ''
        instructor_nombre = (request.POST.get('instructor_nombre', '') or '').strip().upper() or ''
        instructor_cedula = re.sub(r'\D', '', request.POST.get('instructor_cedula', '') or '') or ''
        if tuplas_aprendices is None:
            tipos = request.POST.getlist('apr_tipo_doc[]') or request.POST.getlist('apr_tipo_doc') or []
            nums = request.POST.getlist('apr_num_doc[]') or request.POST.getlist('apr_num_doc') or []
            noms = request.POST.getlist('apr_nombre[]') or request.POST.getlist('apr_nombre') or []
            correos = request.POST.getlist('apr_correo[]') or request.POST.getlist('apr_correo') or []
            tels = request.POST.getlist('apr_telefono[]') or request.POST.getlist('apr_telefono') or []
            n = max(len(tipos), len(nums), len(noms), len(correos), len(tels))
            tuplas_aprendices = []
            for i in range(n):
                t = (tipos[i] if i < len(tipos) else '').strip() or 'CC'
                nd = re.sub(r'\D', '', (nums[i] if i < len(nums) else '') or '')
                nm = (noms[i] if i < len(noms) else '').strip().upper() or ''
                co = (correos[i] if i < len(correos) else '').strip().lower() or ''
                tl = re.sub(r'\D', '', (tels[i] if i < len(tels) else '') or '')
                tuplas_aprendices.append((t, nd, nm, co, tl))
        aprendices = []
        for t, nd, nm, co, tl in tuplas_aprendices:
            aprendices.append({
                'tipo_doc': t or 'CC',
                'num_doc': nd or '',
                'nombre': nm or '',
                'correo': co or '',
                'telefono': tl or '',
            })
        return {
            'municipio': municipio,
            'nombre_ie': nombre_ie,
            'nombre_programa': nombre_programa,
            'codigo_ficha': codigo_ficha,
            'nombre_proyecto': nombre_proyecto,
            'instructor_nombre': instructor_nombre,
            'instructor_cedula': instructor_cedula,
            'aprendices': aprendices,
        }

    def _render_wizard(self, request, valores_previos=None, resumen_exito=None):
        """Renderiza el template wizard_registro.html, opcionalmente con datos previos o resumen de éxito."""
        import json
        ctx = self._get_wizard_context(request)
        if valores_previos is not None:
            ctx['valores_previos_json'] = json.dumps(valores_previos, ensure_ascii=False, default=str)
        else:
            ctx['valores_previos_json'] = ''
        if resumen_exito is not None:
            ctx['resumen_exito_json'] = json.dumps(resumen_exito, ensure_ascii=False, default=str)
        else:
            ctx['resumen_exito_json'] = ''
        return render(request, 'simple/wizard_registro.html', ctx)

    def get(self, request, paso=1, **_ignorado):
        return self._render_wizard(request, valores_previos=None, resumen_exito=None)

    def post(self, request, paso=1, **_ignorado):
        evento = _evento_activo()
        if not evento:
            messages.error(request, 'No hay un evento ACTIVO. Crea primero un evento desde Administración.')
            return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

        try:
            import re
            max_ap = settings.MAX_APRENDICES_POR_PROYECTO
            RE_EMAIL = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
            RE_NUM7 = re.compile(r'^\d{7}$')
            RE_NUM5_15 = re.compile(r'^\d{5,15}$')
            RE_NUM7_15 = re.compile(r'^\d{7,15}$')

            # ---- DATOS DEL PROYECTO / FICHA ----
            nombre_ie = (request.POST.get('nombre_ie', '') or '').strip().upper() or ''
            municipio_ie = (request.POST.get('municipio_ie', '') or '').strip() or 'Riohacha'
            nombre_programa = (request.POST.get('nombre_programa', '') or '').strip().upper() or ''
            nombre_proyecto = (request.POST.get('nombre_proyecto', '') or '').strip().upper() or ''
            codigo_ficha_raw = request.POST.get('codigo_ficha', request.POST.get('codigo_proyecto', '') or '').strip()
            codigo_ficha = re.sub(r'\D', '', codigo_ficha_raw)
            nombre_instructor = (request.POST.get('instructor_nombre', '') or '').strip().upper() or ''
            cedula_instructor_raw = (request.POST.get('instructor_cedula', '') or '').strip()
            cedula_instructor = re.sub(r'\D', '', cedula_instructor_raw)

            if not nombre_ie or not nombre_programa or not nombre_proyecto:
                messages.error(request, '⚠ Faltan datos obligatorios: Institución, Programa y Nombre del proyecto.')
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

            if not nombre_instructor or not cedula_instructor:
                messages.error(request, '⚠ El Instructor líder y su Documento de identidad son OBLIGATORIOS.')
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))
            if not RE_NUM5_15.match(cedula_instructor):
                messages.error(
                    request,
                    f'⚠ Documento del instructor líder inválido: "{cedula_instructor_raw}".\n'
                    f'Sólo se admiten DÍGITOS, entre 5 y 15 caracteres.'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

            if not codigo_ficha or not RE_NUM7.match(codigo_ficha):
                messages.error(
                    request,
                    f'⚠ El Código de Ficha es obligatorio y debe tener EXACTAMENTE 7 dígitos numéricos.\n'
                    f'Valor recibido: "{codigo_ficha_raw}" → "{codigo_ficha}" ({len(codigo_ficha)} dígitos).'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

            # ---- INSTITUCIÓN + PROGRAMA (SOLO CATÁLOGO ADMIN — NO se crean nuevos desde registro) ----
            colegio = InstitucionEducativa.objects.filter(nombre__iexact=nombre_ie, activo=True).order_by('id').first()
            if not colegio:
                messages.error(
                    request,
                    f'❌ La Institución Educativa "{nombre_ie}" NO EXISTE en el catálogo del administrador.\n'
                    'No se puede crear desde el registro de proyectos: el Administrador debe crearla manualmente o por Excel.'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

            programa = ProgramaTecnico.objects.filter(nombre__iexact=nombre_programa, activo=True).order_by('id').first()
            if not programa:
                messages.error(
                    request,
                    f'❌ El Programa Técnico "{nombre_programa}" NO EXISTE en el catálogo del administrador.\n'
                    'No se puede crear desde el registro de proyectos: el Administrador debe crearlo manualmente o por Excel.'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

            # ---- INSTRUCTOR LÍDER = OPCIÓN A (ESTRICTAMENTE CATÁLOGO) ----
            # Regla Opción A aprobada por usuario: Instructor LÍDER viene ÚNICAMENTE del
            # maestro Ficha.instructor_lider. NO se usa NADA de lo que el formulario
            # envíe (inputs readonly, el usuario NO puede escribir/editar). Si la Ficha
            # no tiene instructor_lider asignado en el catálogo Admin → ERROR DURO (no
            # se crea Persona, no se crea Instructor, no se guarda Proyecto).
            instructor_obj = None

            # ---- FICHA MAESTRA (SOLO CATÁLOGO ADMIN — DEBE EXISTIR; no se crea aquí) ----
            ficha_obj = Ficha.objects.filter(numero=codigo_ficha, activo=True).first()
            if not ficha_obj:
                messages.error(
                    request,
                    f'❌ La Ficha #{codigo_ficha} NO EXISTE en el catálogo del administrador.\n'
                    'No se puede crear desde aquí: el Administrador debe dar de alta la ficha (Institución + Programa + Instructor líder).'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))
            # Coherencia entre la ficha existente y la selección actual
            if ficha_obj.institucion_id != colegio.pk or ficha_obj.programa_id != programa.pk:
                messages.warning(
                    request,
                    f'ℹ Se usó la información MAESTRA de la Ficha #{codigo_ficha} (Institución/Programa).\n'
                    f'Selección usuario: IE="{nombre_ie}" · Programa="{nombre_programa}" → Ficha: IE="{ficha_obj.institucion.nombre}" · Programa="{ficha_obj.programa.nombre}".'
                )
                colegio = ficha_obj.institucion
                programa = ficha_obj.programa
            # ================ OPCIÓN A INICIO: SOLO instructor_lider de FICHA ==============
            if not ficha_obj.instructor_lider_id:
                messages.error(
                    request,
                    f'❌ La Ficha #{codigo_ficha} NO tiene Instructor Líder asignado en el catálogo maestro.\n'
                    'El formulario NO permite registrar manualmente el instructor (dato catálogo maestro SENA). '
                    'Por favor contacte al Administrador para que cargue el Instructor líder de la Ficha '
                    f'#{codigo_ficha} mediante la importación Excel o el panel administrativo.'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))
            p_lider = getattr(ficha_obj.instructor_lider, 'persona', None)
            if not p_lider:
                messages.error(
                    request,
                    f'❌ La Ficha #{codigo_ficha} tiene Instructor Líder sin registro de Persona. '
                    'Contacte al Administrador para corregir la integridad de datos del instructor.'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))
            instructor_obj = ficha_obj.instructor_lider
            nombre_instructor = p_lider.nombre_completo
            cedula_instructor = p_lider.numero_identificacion
            # Relación Instructor <-> Programa (compatibilidad)
            if programa.pk and not instructor_obj.programas.filter(pk=programa.pk).exists():
                try:
                    instructor_obj.programas.add(programa)
                except Exception:
                    pass
            # ================ OPCIÓN A FIN: ya NO se usa el instructor que venga del form POST ==============
            if ficha_obj.municipio:
                municipio_ie = ficha_obj.municipio

            # ---- APRENDICES (SUB-FORMULARIO DINÁMICO, arreglos) ----
            tipos = request.POST.getlist('apr_tipo_doc[]') or request.POST.getlist('apr_tipo_doc') or []
            nums = request.POST.getlist('apr_num_doc[]') or request.POST.getlist('apr_num_doc') or []
            noms = request.POST.getlist('apr_nombre[]') or request.POST.getlist('apr_nombre') or []
            correos = request.POST.getlist('apr_correo[]') or request.POST.getlist('apr_correo') or []
            tels = request.POST.getlist('apr_telefono[]') or request.POST.getlist('apr_telefono') or []

            n = max(len(tipos), len(nums), len(noms), len(correos), len(tels))
            tuplas = []
            for i in range(n):
                t = (tipos[i] if i < len(tipos) else '').strip() or 'CC'
                nd_raw = (nums[i] if i < len(nums) else '') or ''
                nd = re.sub(r'\D', '', nd_raw)
                nm = (noms[i] if i < len(noms) else '').strip().upper() or ''
                co = (correos[i] if i < len(correos) else '').strip().lower() or ''
                tl_raw = (tels[i] if i < len(tels) else '') or ''
                tl = re.sub(r'\D', '', tl_raw)

                # Skip filas completamente vacías (sin doc ni nombre)
                if not nd and not nm:
                    continue

                # Validación: TODOS los campos obligatorios INCLUYENDO teléfono
                faltan = []
                if not nd: faltan.append('N° Documento')
                if not nm: faltan.append('Nombre completo')
                if not co: faltan.append('Correo electrónico')
                if not tl: faltan.append('Teléfono')
                if faltan:
                    messages.error(
                        request,
                        f'⚠ El aprendiz #{i+1} tiene campos obligatorios vacíos: {", ".join(faltan)}.\n'
                        'Todos los campos son obligatorios (incluye Teléfono).'
                    )
                    return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

                # Validación FORMATO estricto por campo
                errores_fmt = []
                if not RE_NUM5_15.match(nd):
                    errores_fmt.append(
                        f'N° Documento "{nd_raw}" → debe tener SOLO dígitos, entre 5 y 15 caracteres (tienes {len(nd)}).'
                    )
                if not RE_EMAIL.match(co):
                    errores_fmt.append(
                        f'Correo electrónico "{co}" → estructura inválida (debe ser como usuario@dominio.ext).'
                    )
                if not RE_NUM7_15.match(tl):
                    errores_fmt.append(
                        f'Teléfono "{tl_raw}" → debe tener SOLO dígitos, entre 7 y 15 caracteres (tienes {len(tl)}).'
                    )
                if errores_fmt:
                    messages.error(
                        request,
                        f'❌ El aprendiz #{i+1} tiene campos con formato incorrecto:\n  • '
                        + '\n  • '.join(errores_fmt)
                    )
                    return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

                tuplas.append((t, nd, nm, co, tl))

            # ================ NUEVO v31: BLOQUEO SI EL APRENDIZ YA ESTÁ EN OTRO PROYECTO (ANTES DE CREAR NADA) ================
            numeros_en_submision = set()
            for i, (t, nd, nm, co, tl) in enumerate(tuplas):
                if nd in numeros_en_submision:
                    messages.error(
                        request,
                        f'❌ DUPLICADO EN EL FORMULARIO: El aprendiz #{i+1} "{nm}" (Documento {nd}) '
                        'ya está incluido varias veces en este mismo registro. '
                        'Por favor elimina las filas repetidas.'
                    )
                    return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))
                numeros_en_submision.add(nd)
                # Búsqueda transversal: Mismo número de documento (INDEPENDIENTEMENTE DE TIPO DOC) en BD
                num_solo_dig = re.sub(r'\D', '', nd) or None
                if not num_solo_dig:
                    continue
                qs_personas_con_este_num = Persona.objects.filter(
                    numero_identificacion__regex=rf'^0*{num_solo_dig}0*$'
                ).exclude(tipo_persona='APRENDIZ')
                # Busca específicamente en APRENDICES (incluyendo si originalmente no era tipo_persona APRENDIZ pero sí Aprendiz)
                qs_aprendiz_duplicado = (
                    Aprendiz.objects
                    .select_related('persona', 'proyecto', 'proyecto__ficha')
                    .filter(persona__numero_identificacion__regex=rf'^0*{num_solo_dig}0*$')
                )
                existente = qs_aprendiz_duplicado.first()
                if existente:
                    p_repetida = existente.persona
                    nombre_completo_bd = p_repetida.nombre_completo or nm
                    nombre_proy_original = (getattr(getattr(existente, 'proyecto', None), 'nombre', '') or '') or 'Proyecto sin nombre'
                    codigo_proy_original = (getattr(getattr(existente, 'proyecto', None), 'codigo', '') or '') or 'sin código'
                    ficha_num = ''
                    if existente.proyecto and existente.proyecto.ficha_id:
                        ficha_num = f' · Ficha #{existente.proyecto.ficha.numero}'
                    ie_original = ''
                    if existente.proyecto and existente.proyecto.institucion_id:
                        ie_original = f' · IE: {existente.proyecto.institucion.nombre}'
                    messages.error(
                        request,
                        f'🚫 ESTE APRENDIZ YA ESTÁ INSCRITO EN OTRO PROYECTO (regla 1 aprendiz = 1 proyecto):\n'
                        f'  • Aprendiz #{i+1}: "{nm}"\n'
                        f'  • Documento: {p_repetida.tipo_identificacion.codigo} {p_repetida.numero_identificacion}\n'
                        f'  • Ya registrado como: "{nombre_completo_bd}"\n'
                        f'  • PROYECTO ACTUAL: "{nombre_proy_original}" (Código {codigo_proy_original}{ficha_num}{ie_original})\n'
                        f'  • Nombre de proyecto nuevo que intentaste inscribirlo: "{nombre_proyecto}"\n'
                        f'❕ Cómo solucionarlo: (1) Ve al listado de Proyectos y elimina al aprendiz del proyecto original, '
                        f'o (2) Usa el proyecto original, o (3) Contacta al Administrador.'
                    )
                    return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))
                # También bloqueamos si existe Persona con ese mismo #DOC como INVITADO/INSTRUCTOR/ORGANIZADOR PERO CON tipo_persona != APRENDIZ pero queremos pasarlo a Aprendiz
                # — NADA: permitimos que la misma persona cambie de rol (ej: persona era Invitado y ahora es Aprendiz, es válido).
                # Lo único que NO se permite es 2 Aprendices del MISMO #DOC = regla anterior.

            # Capo MAX por configuración
            if len(tuplas) > max_ap:
                messages.warning(request, f'⚠ Máximo permitido {max_ap} aprendices por ficha. Se guardaron sólo los primeros {max_ap}.')
                tuplas = tuplas[:max_ap]

            if len(tuplas) == 0:
                messages.warning(request, 'ℹ No se incluyeron aprendices. Puedes agregarlos después editando la ficha.')

            # ================ TRANSACCIÓN ATÓMICA: O TODO SE GUARDA, O NADA SE GUARDA (ROLLBACK SI ALGO FALLA) ================
            try:
                with transaction.atomic():
                    proyecto = Proyecto(
                        evento=evento,
                        nombre=nombre_proyecto,
                        descripcion=f'{nombre_proyecto} - {colegio.nombre}',
                        institucion=colegio,
                        programa=programa,
                        instructor_responsable=instructor_obj,
                        estado='APROBADO',
                    )
                    if ficha_obj:
                        proyecto.ficha = ficha_obj
                    proyecto.save()  # save() genera el código secuencial único por evento+ficha

                    aprendices_guardados = 0
                    aprendices_resumen = []
                    for t, nd, nm, co, tl in tuplas:
                        nombres_a, apellidos_a = self._separar_nombres_apellidos(nm)
                        persona_a, _ = Persona.objects.get_or_create(
                            tipo_identificacion=_obtener_tipo_id(t),
                            numero_identificacion=nd,
                            defaults={
                                'nombres': (nombres_a or '').upper(),
                                'apellidos': (apellidos_a or '').upper(),
                                'correo': co,
                                'telefono': tl or None,
                                'tipo_persona': 'APRENDIZ',
                            },
                        )
                        # Actualizar correo / teléfono si cambió (y hay valor nuevo no vacío para correo)
                        need_save = False
                        upd_fields = []
                        if persona_a.correo != co and co:
                            persona_a.correo = co
                            upd_fields.append('correo')
                            need_save = True
                        if tl and persona_a.telefono != tl:
                            persona_a.telefono = tl
                            upd_fields.append('telefono')
                            need_save = True
                        nombres_up = (nombres_a or '').upper()
                        apellidos_up = (apellidos_a or '').upper()
                        if persona_a.nombres != nombres_up:
                            persona_a.nombres = nombres_up
                            upd_fields.append('nombres')
                            need_save = True
                        if persona_a.apellidos != apellidos_up:
                            persona_a.apellidos = apellidos_up
                            upd_fields.append('apellidos')
                            need_save = True
                        # Si la persona no era APRENDIZ aún, actualízala a APRENDIZ
                        if persona_a.tipo_persona != 'APRENDIZ':
                            persona_a.tipo_persona = 'APRENDIZ'
                            upd_fields.append('tipo_persona')
                            need_save = True
                        if need_save and upd_fields:
                            persona_a.save(update_fields=upd_fields)

                        # NUEVO v31: NO usamos get_or_create con defaults, porque si ya existía perfil_aprendiz
                        # (OneToOne) debe fallar. En su lugar usamos el patrón seguro:
                        # --- Bloqueo double check final + full_clean() para forzar validación del modelo clean() ---
                        tiene_perfil = bool(getattr(persona_a, 'perfil_aprendiz_id', None))
                        if tiene_perfil:
                            # CASO IMPOSIBLE por la validación anterior, pero por si acaso (race conditions 2 usuarios concurrentes):
                            perfil_viejo = Aprendiz.objects.select_related('proyecto').get(pk=persona_a.perfil_aprendiz_id)
                            viejo_proy = f'"{perfil_viejo.proyecto.nombre}" (Código {perfil_viejo.proyecto.codigo})' if perfil_viejo.proyecto else 'otro proyecto'
                            raise Exception(
                                f'⚠ Concurrencia: "{persona_a.nombre_completo}" ya fue inscrito en otro proyecto en este mismo instante: {viejo_proy}.'
                            )
                        # Creamos PERFIL DE APRENDIZ NUEVO
                        entidad_auto = (str(colegio.nombre) or '').upper() or None
                        nuevo_aprendiz = Aprendiz(
                            persona=persona_a,
                            proyecto=proyecto,
                            grado='11',
                            entidad=entidad_auto,
                            cargo='Aprendiz',
                        )
                        # === EJECUTA LAS VALIDACIONES DEL MODELO (clean()): NO 2 proyectos, NO mismo #DOC ===
                        nuevo_aprendiz.full_clean()
                        nuevo_aprendiz.save(force_insert=True)
                        aprendices_guardados += 1
                        aprendices_resumen.append({
                            'tipo_doc': t or 'CC',
                            'num_doc': nd or '',
                            'nombre': nm or '',
                            'correo': co or '',
                            'telefono': tl or '',
                        })
            except Exception as e_err:
                messages.error(
                    request,
                    f'❌ NO SE PUDO GUARDAR EL PROYECTO (se deshizo todo): {e_err}'
                )
                return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

            total_proyectos_ficha = 0
            if ficha_obj:
                total_proyectos_ficha = Proyecto.objects.filter(
                    evento=evento,
                    ficha=ficha_obj,
                ).count()
            # ===== Resumen para MODAL ÉXITO (auto-abierto al re-renderizar wizard) =====
            try:
                from datetime import datetime as _dt_wiz
                try:
                    from zoneinfo import ZoneInfo as _ZI
                    _tz = _ZI('America/Bogota')
                except Exception:
                    try:
                        import pytz as _pytz
                        _tz = _pytz.timezone('America/Bogota')
                    except Exception:
                        _tz = None
                _ahora = _dt_wz.now(tz=_tz) if _tz else _dt_wz.now()
                _fhr = _ahora.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                _fhr = ''
            resumen_exito = {
                'ok': True,
                'codigo_proyecto': (proyecto.codigo or '') if proyecto else '',
                'numero_proyecto_ficha': total_proyectos_ficha if total_proyectos_ficha else 1,
                'ficha_numero': str(ficha_obj.numero) if ficha_obj else (codigo_ficha or ''),
                'nombre_proyecto': (proyecto.nombre or nombre_proyecto) if proyecto else (nombre_proyecto or ''),
                'ie_nombre': (colegio.nombre or '') if colegio else nombre_ie,
                'ie_municipio': (str(colegio.municipio.nombre) or '') if (colegio and colegio.municipio_id) else (municipio_ie or ''),
                'programa_nombre': (programa.nombre or '') if programa else nombre_programa,
                'instructor_nombre': nombre_instructor or '',
                'instructor_cedula': cedula_instructor or '',
                'cantidad_aprendices': aprendices_guardados or 0,
                'aprendices': aprendices_resumen or [],
                'fecha_hora_registro': _fhr,
            }
            msg = (
                f'✔ Ficha #{codigo_ficha} · Código Proyecto: "{resumen_exito["codigo_proyecto"]}" · '
                f'Proyecto #{resumen_exito["numero_proyecto_ficha"]} en esta ficha · '
                f'Nombre: "{resumen_exito["nombre_proyecto"]}" · {resumen_exito["cantidad_aprendices"]} aprendiz(es) · '
                f'{resumen_exito["ie_nombre"]}'
            )
            if resumen_exito['ie_municipio']:
                msg += f' ({resumen_exito["ie_municipio"]})'
            msg += '.'
            messages.success(request, msg)
            # ====== POST OK (302 NO más redirect): mismo wizard URL, FORMULARIO VACÍO + MODAL ÉXITO auto-abierto ======
            return self._render_wizard(request, valores_previos=None, resumen_exito=resumen_exito)

        except Exception as e:
            messages.error(request, f'⚠ Hubo un error al guardar: {e}')
            return self._render_wizard(request, valores_previos=self._extract_valores_previos(request))

    @staticmethod
    def _separar_nombres_apellidos(texto):
        import re
        texto = (texto or '').strip()
        if not texto:
            return 'Sin', 'Nombre'
        partes = re.split(r'\s+', texto)
        if len(partes) == 1:
            return partes[0], 'S.A.'
        if len(partes) == 2:
            return partes[0], partes[1]
        if len(partes) == 3:
            return partes[0], ' '.join(partes[1:])
        return ' '.join(partes[:2]), ' '.join(partes[2:])


# ============================================================
# AUTOCOMPLETADO - BÚSQUEDA RÁPIDA (Instituciones, Programas, Instructores por AJAX)
# ============================================================
class BuscarAjaxView(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return JsonResponse({'ok': False, 'mensaje': 'Autenticación requerida'})
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        tipo = request.GET.get('tipo', '')
        q = request.GET.get('q', '').strip()
        if tipo == 'institucion':
            qs = InstitucionEducativa.objects.filter(nombre__icontains=q).select_related('municipio').order_by('nombre')[:15]
            data = []
            for ie in qs:
                data.append({
                    'id': ie.id,
                    'nombre': ie.nombre,
                    'municipio': ie.municipio.nombre if ie.municipio_id else ''
                })
            data = list(data)
        elif tipo == 'programa':
            data = list(
                ProgramaTecnico.objects.filter(nombre__icontains=q).order_by('nombre')[:15].values('id', 'nombre')
            )
        elif tipo == 'instructor':
            data = list(
                Instructor.objects.select_related('persona').filter(
                    persona__nombres__icontains=q
                ) | Instructor.objects.select_related('persona').filter(
                    persona__apellidos__icontains=q
                ).order_by('persona__apellidos')[:15]
            )
            data = [{'id': i.pk, 'nombre': i.persona.get_full_name(), 'cedula': i.persona.numero_identificacion} for i in data]
        else:
            data = []
        return JsonResponse({'ok': True, 'data': data})


# ============================================================
# PANTALLAS MÓVILES OPERADOR (ASISTENCIA / REFRIGERIOS / CERTIFICADOS)
# ============================================================
class OperadorMobileView(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'operadores')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, tipo='asistencia', **_ignorado):
        evento = _evento_activo()
        total = 0
        ingresaron = 0
        faltan = 0
        porcentaje = 0
        if evento:
            try:
                from django.db.models import Q
                qs = Persona.objects.filter(
                    Q(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']),
                    activo=True,
                )
                total = qs.count()
                if tipo == 'asistencia':
                    ids = set(AsistenciaEvento.objects.filter(evento=evento).values_list('persona_id', flat=True))
                    ingresaron = len(ids)
                elif tipo == 'refrigerios':
                    svc = _servicio_almuerzo(evento)
                    if svc:
                        ids = set(EntregaServicio.objects.filter(evento=evento, tipo_servicio=svc).values_list('persona_id', flat=True))
                        ingresaron = len(ids)
                elif tipo == 'certificados':
                    ids = set(Certificado.objects.filter(evento=evento).values_list('persona_id', flat=True))
                    ingresaron = len(ids)
                faltan = max(total - ingresaron, 0)
                porcentaje = round((ingresaron / total) * 100, 1) if total > 0 else 0
            except Exception:
                pass
        tok_pub = getattr(settings, 'TOKEN_OPERADORES_PUBLICO', '') or ''
        return render(request, 'simple/operador_mobile.html', {
            'tipo': tipo,
            'evento': evento,
            'servicio': _servicio_almuerzo(evento) if tipo == 'refrigerios' else None,
            'stats_iniciales': {
                'total': total, 'ingresaron': ingresaron, 'faltan': faltan, 'porcentaje': porcentaje,
            },
            'token_operadores_publico': tok_pub,
        })


# ============================================================
# STATS EN VIVO — Polling Panel Operador Móvil (2 tarjetas)
#   Parámetro URL: ?tipo=asistencia|refrigerios|certificados
# ============================================================
@method_decorator(csrf_exempt, name='dispatch')
class StatsOperadorAjax(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'operadores')
        if resp is not None:
            # Si helper ya devolvió un JsonResponse (con code/mensaje específico), lo propagamos.
            if isinstance(resp, JsonResponse):
                return resp
            return JsonResponse({'ok': False, 'total': 0, 'ingresaron': 0, 'faltan': 0, 'porcentaje': 0, 'ts': None,
                                 'mensaje': 'Autenticación requerida. Usa el enlace público /o/<TOKEN>/asistencia/.',
                                 'code': 'AUTH_REQUIRED', 'status': 'ROJO'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        tipo = (request.GET.get('tipo') or 'asistencia').strip().lower()
        evento = _evento_activo()
        if not evento:
            return JsonResponse({'ok': False, 'tipo': tipo, 'total': 0, 'ingresaron': 0, 'faltan': 0, 'porcentaje': 0, 'ts': None})
        try:
            from django.db.models import Q
            qs_personas_feria = Persona.objects.filter(
                Q(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']),
                activo=True,
            )
            total = qs_personas_feria.count()
            if tipo == 'asistencia':
                ids_ingresados = set(AsistenciaEvento.objects.filter(evento=evento).values_list('persona_id', flat=True))
                ingresaron = len(ids_ingresados)
            elif tipo == 'refrigerios':
                svc = _servicio_almuerzo(evento)
                if svc:
                    ids_ingresados = set(EntregaServicio.objects.filter(evento=evento, tipo_servicio=svc).values_list('persona_id', flat=True))
                    ingresaron = len(ids_ingresados)
                else:
                    ingresaron = 0
            elif tipo == 'certificados':
                ids_ingresados = set(Certificado.objects.filter(evento=evento).values_list('persona_id', flat=True))
                ingresaron = len(ids_ingresados)
            else:
                ids_ingresados = set(AsistenciaEvento.objects.filter(evento=evento).values_list('persona_id', flat=True))
                ingresaron = len(ids_ingresados)
            faltan = max(total - ingresaron, 0)
            porcentaje = round((ingresaron / total) * 100, 1) if total > 0 else 0
            from datetime import datetime
            return JsonResponse({
                'ok': True, 'tipo': tipo, 'evento_id': evento.id,
                'total': total, 'ingresaron': ingresaron, 'faltan': faltan,
                'porcentaje': porcentaje, 'ts': datetime.now().strftime('%H:%M:%S'),
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e), 'total': 0, 'ingresaron': 0, 'faltan': 0, 'porcentaje': 0, 'ts': None})


# ============================================================
# STATS EN VIVO — Polling Panel Admin (Ingresados vs Faltan)
# ============================================================
class StatsOperativosAjax(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']

    def get(self, request, **_ignorado):
        evento = _evento_activo()
        if not evento:
            return JsonResponse({
                'ok': False, 'evento': None,
                'total_personas': 0, 'ingresaron': 0, 'faltan': 0,
                'refrigerios': 0, 'certificados': 0, 'porcentaje': 0, 'ts': None,
            })
        try:
            from django.db.models import Q
            qs_personas_feria = Persona.objects.filter(
                Q(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO']),
                activo=True,
            )
            total = qs_personas_feria.count()
            ids_ingresados = set(
                AsistenciaEvento.objects.filter(evento=evento)
                .values_list('persona_id', flat=True)
            )
            ingresaron = len(ids_ingresados)
            faltan = max(total - ingresaron, 0)
            svc = _servicio_almuerzo(evento)
            refrigerios = EntregaServicio.objects.filter(evento=evento, tipo_servicio=svc).count() if svc else 0
            certificados = Certificado.objects.filter(evento=evento).count()
            porcentaje = round((ingresaron / total) * 100, 1) if total > 0 else 0
            from datetime import datetime
            return JsonResponse({
                'ok': True,
                'evento': {'id': evento.id, 'nombre': evento.nombre, 'municipio': evento.municipio or ''},
                'total_personas': total, 'ingresaron': ingresaron, 'faltan': faltan,
                'refrigerios': refrigerios, 'certificados': certificados,
                'porcentaje': porcentaje,
                'ts': datetime.now().strftime('%H:%M:%S'),
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class RegistrarOperadorAjax(View):
    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'operadores')
        if resp is not None:
            # Si helper ya devolvió un JsonResponse (con code/mensaje específico), lo propagamos.
            if isinstance(resp, JsonResponse):
                return resp
            return JsonResponse({
                'ok': False, 'status': 'ROJO',
                'mensaje': 'Autenticación requerida. Usa el enlace público /o/<TOKEN>/asistencia/ generado desde el Panel Admin.',
                'code': 'AUTH_REQUIRED'
            }, status=401)
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, **_ignorado):
        try:
            import json
            body = json.loads(request.body or '{}')
        except Exception:
            body = request.POST.dict()
        token = (body.get('token') or body.get('qr_token') or '').strip()
        numero_documento_req = (body.get('numero_documento') or '').strip()
        medio = (body.get('medio') or 'QR').strip()[:20] or 'QR'
        tipo = body.get('tipo') or 'asistencia'
        evento = _evento_activo()

        if not evento:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'No hay evento activo.'})

        # === CASO A) QR TOKEN (método normal) ===
        if token:
            persona = Persona.objects.filter(qr_token=token).first()
            if not persona:
                return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'Código QR no registrado en el sistema.'})
        # === CASO B) INGRESO MANUAL POR NÚMERO DE DOCUMENTO (fallback sin escarapela) ===
        elif numero_documento_req:
            import re
            _numdoc = re.sub(r'\D', '', numero_documento_req or '')
            if not _numdoc or len(_numdoc) < 5 or len(_numdoc) > 15:
                return JsonResponse({
                    'ok': False, 'status': 'ROJO',
                    'mensaje': f'Número de documento inválido ("{_numdoc}"). Debe contener entre 5 y 15 dígitos numéricos.'
                })
            persona = Persona.objects.filter(numero_identificacion=_numdoc).first()
            if not persona:
                return JsonResponse({
                    'ok': False, 'status': 'ROJO',
                    'mensaje': f'No existe ninguna persona registrada con el N° de documento "{_numdoc}". Verifique el número.'
                })
            medio = 'MANUAL'
        else:
            return JsonResponse({
                'ok': False, 'status': 'ROJO',
                'mensaje': 'Proporcione un código QR o un N° de documento.'
            })

        label = persona.get_full_name()
        extra = ''
        tipo_asistente = 'Persona'
        nombre_proyecto = ''
        ficha_codigo = ''
        try:
            if persona.tipo_persona == 'APRENDIZ':
                tipo_asistente = 'Aprendiz Con Proyecto'
                if hasattr(persona, 'perfil_aprendiz') and persona.perfil_aprendiz:
                    nombre_proyecto = persona.perfil_aprendiz.proyecto.nombre if persona.perfil_aprendiz.proyecto else ''
                    ficha_codigo = persona.perfil_aprendiz.proyecto.ficha.numero if (persona.perfil_aprendiz.proyecto and persona.perfil_aprendiz.proyecto.ficha) else ''
                    extra = ' · Proyecto: ' + (nombre_proyecto or 'Sin asignar')
                    if ficha_codigo:
                        extra += ' · Ficha: ' + ficha_codigo
            elif persona.tipo_persona == 'INSTRUCTOR':
                tipo_asistente = 'Instructor'
                extra = ' · Instructor SENA'
            elif persona.tipo_persona == 'INVITADO':
                tipo_asistente = 'Invitado Especial'
                extra = ' · Invitado a la feria'
        except Exception:
            pass
        tipo_doc = getattr(persona.tipo_identificacion, 'codigo', None) if persona.tipo_identificacion else ''
        tipo_doc = (tipo_doc or 'CC').strip()[:5] or 'CC'
        numero_doc = persona.numero_identificacion or ''

        operador = _operador_para_guardar(request)
        if not operador:
            return JsonResponse({
                'ok': False, 'status': 'ROJO',
                'mensaje': 'No se pudo determinar el operador. Inicia sesión o usa el enlace token correcto.',
            })

        try:
            if tipo == 'asistencia':
                _, created = AsistenciaEvento.objects.get_or_create(
                    evento=evento, persona=persona,
                    defaults={'operador': operador, 'medio': medio},
                )
                status = 'VERDE' if created else 'AMARILLO'
                mensaje = 'Ingreso registrado ✔' if created else '⚠ Ya había ingresado antes'
            elif tipo == 'refrigerios':
                svc = _servicio_almuerzo(evento)
                _, created = EntregaServicio.objects.get_or_create(
                    evento=evento, persona=persona, tipo_servicio=svc,
                    defaults={'operador': operador, 'medio': medio},
                )
                status = 'VERDE' if created else 'AMARILLO'
                mensaje = f'{svc.nombre} entregado ✔' if created else '⚠ Ya se le había entregado'
            elif tipo == 'certificados':
                obj, created = Certificado.objects.get_or_create(
                    evento=evento, persona=persona,
                    defaults={'operador': operador, 'medio': medio},
                )
                if not obj.codigo_unico:
                    obj.save()
                status = 'VERDE'
                mensaje = 'Certificado entregado ✔ Código: ' + obj.codigo_unico
            else:
                return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': 'Tipo desconocido.'})
        except Exception as e:
            return JsonResponse({'ok': False, 'status': 'ROJO', 'mensaje': f'Error: {e}'})

        nombre_ie = ''
        municipio_persona = ''
        correo = ''
        telefono = ''
        try:
            correo = getattr(persona, 'correo', '') or ''
            telefono = getattr(persona, 'telefono', '') or ''
        except Exception:
            pass

        return JsonResponse({
            'ok': True,
            'status': status,
            'mensaje': mensaje,
            'nombre': label,
            'rol': (persona.tipo_persona or '').title(),
            'tipo_asistente': tipo_asistente,
            'tipo_documento': tipo_doc,
            'numero_documento': numero_doc,
            'correo': correo,
            'telefono': telefono,
            'es_duplicado': (status == 'AMARILLO'),
            'es_nuevo': (status == 'VERDE'),
        })


# ============================================================
# DASHBOARD GERENCIAL PROFESIONAL - TIEMPO REAL
# ============================================================
class DashboardSimpleView(LoginRequiredMixin, View):
    def get(self, request, **_ignorado):
        from django.db.models import Count, Q, F, DateTimeField
        from django.db.models.functions import TruncHour, ExtractHour
        from django.utils import timezone

        evento = _evento_activo()
        if not evento:
            return render(request, 'simple/dashboard.html', {'evento': None})

        qs_personas = Persona.objects.all()
        total_personas = qs_personas.count()
        total_por_rol = dict(qs_personas.values_list('tipo_persona').annotate(c=Count('id')))
        total_aprendices = total_por_rol.get('APRENDIZ', 0)
        total_instructores = total_por_rol.get('INSTRUCTOR', 0)
        total_invitados = total_por_rol.get('INVITADO', 0)
        total_organizadores = total_por_rol.get('ORGANIZADOR', 0)
        total_visitantes = total_por_rol.get('VISITANTE', 0)

        total_proyectos = Proyecto.objects.filter(evento=evento).count()
        qs_proy_evento = Proyecto.objects.filter(evento=evento)
        try:
            total_instituciones_inscritas = (
                InstitucionEducativa.objects
                .filter(id__in=qs_proy_evento.values('institucion_id'))
                .values('id')
                .distinct()
                .count()
            )
        except Exception:
            total_instituciones_inscritas = 0
        try:
            total_programas_unicos = (
                ProgramaTecnico.objects
                .filter(id__in=qs_proy_evento.values('programa_id'))
                .values('id')
                .distinct()
                .count()
            )
        except Exception:
            total_programas_unicos = 0
        try:
            qs_ficha_ids = Aprendiz.objects.filter(
                proyecto__evento=evento,
                ficha_id__isnull=False,
            ).values('ficha_id')
            total_fichas_unicas = Ficha.objects.filter(id__in=qs_ficha_ids).values('id').distinct().count()
        except Exception:
            total_fichas_unicas = 0
        total_personas_estructura = (
            total_aprendices + total_instructores + total_invitados
            + total_organizadores + total_visitantes
        )
        personas_estructura_desglose = [
            ('Aprendices inscritos', total_aprendices, 'chip-apr',),
            ('Instructores', total_instructores, 'chip-ins',),
            ('Invitados', total_invitados, 'chip-inv',),
            ('Organizadores', total_organizadores, 'chip-org',),
            ('Visitantes (form. futuro)', total_visitantes, 'chip-manual',),
        ]

        qs_asistencia = AsistenciaEvento.objects.filter(evento=evento).select_related('persona', 'operador')
        asistentes_total = qs_asistencia.count()
        asistentes_por_rol = dict(qs_asistencia.values_list('persona__tipo_persona').annotate(c=Count('id')))
        asistentes_aprendices = asistentes_por_rol.get('APRENDIZ', 0)
        asistentes_instructores = asistentes_por_rol.get('INSTRUCTOR', 0)
        asistentes_invitados = asistentes_por_rol.get('INVITADO', 0)
        asistentes_organizadores = asistentes_por_rol.get('ORGANIZADOR', 0)

        asist_qr = qs_asistencia.filter(medio='QR').count()
        asist_manual = qs_asistencia.filter(medio='MANUAL').count()

        ausentes = max(total_personas - asistentes_total, 0)
        pct_asistencia = (asistentes_total * 100 // total_personas) if total_personas else 0

        qs_refrigerios = EntregaServicio.objects.filter(evento=evento).select_related('persona', 'operador', 'tipo_servicio')
        refrigerios_entregados = qs_refrigerios.count()
        refri_por_rol = dict(qs_refrigerios.values_list('persona__tipo_persona').annotate(c=Count('id')))
        refri_aprendices = refri_por_rol.get('APRENDIZ', 0)
        refri_instructores = refri_por_rol.get('INSTRUCTOR', 0)
        refri_invitados = refri_por_rol.get('INVITADO', 0)
        refri_organizadores = refri_por_rol.get('ORGANIZADOR', 0)
        refri_qr = qs_refrigerios.filter(medio='QR').count()
        refri_manual = qs_refrigerios.filter(medio='MANUAL').count()
        refrigerios_pendientes = max(asistentes_total - refrigerios_entregados, 0)
        pct_refrigerios = (refrigerios_entregados * 100 // asistentes_total) if asistentes_total else 0
        _por_tipo_qs = list(qs_refrigerios.values_list('tipo_servicio__nombre').annotate(c=Count('id')).order_by('tipo_servicio__orden', '-c'))
        refrigerios_por_tipo = [(str(n or 'Sin definir'), int(c)) for n, c in _por_tipo_qs]
        _tipos_activos_qs = list(TipoServicio.objects.filter(evento=evento, activo=True).order_by('orden', 'nombre').values_list('nombre', flat=True))
        tipos_servicio_activos = [str(x) for x in _tipos_activos_qs if x]

        qs_certificados = Certificado.objects.filter(evento=evento).select_related('persona', 'operador')
        certificados_entregados = qs_certificados.count()
        cert_por_rol = dict(qs_certificados.values_list('persona__tipo_persona').annotate(c=Count('id')))
        cert_aprendices = cert_por_rol.get('APRENDIZ', 0)
        cert_instructores = cert_por_rol.get('INSTRUCTOR', 0)
        cert_invitados = cert_por_rol.get('INVITADO', 0)
        cert_organizadores = cert_por_rol.get('ORGANIZADOR', 0)
        cert_qr = qs_certificados.filter(medio='QR').count()
        cert_manual = qs_certificados.filter(medio='MANUAL').count()
        certificados_pendientes = max(asistentes_total - certificados_entregados, 0)
        pct_certificados = (certificados_entregados * 100 // asistentes_total) if asistentes_total else 0

        ahora = timezone.localtime(timezone.now()) if timezone.is_aware(timezone.now()) else timezone.now()
        fi = evento.fecha_inicio
        ff = evento.fecha_fin
        estado_evento = 'NO_INICIADO'
        if fi and ff:
            if hasattr(fi, 'year') and not hasattr(fi, 'hour'):
                hoy = ahora.date()
                if hoy < fi: estado_evento = 'NO_INICIADO'
                elif hoy > ff: estado_evento = 'FINALIZADO'
                else: estado_evento = 'EN_CURSO'
            else:
                if ahora < fi: estado_evento = 'NO_INICIADO'
                elif ahora > ff: estado_evento = 'FINALIZADO'
                else: estado_evento = 'EN_CURSO'

        actividad = []
        try:
            for obj in qs_asistencia.order_by('-fecha_hora')[:5]:
                p = obj.persona
                op = obj.operador
                actividad.append({
                    'entrega': obj.fecha_hora,
                    'tipo': 'ASISTENCIA',
                    'doc': getattr(p, 'numero_identificacion', '') or '',
                    'nombres': getattr(p, 'nombres', '') or '',
                    'apellidos': getattr(p, 'apellidos', '') or '',
                    'rol': getattr(p, 'tipo_persona', '') or '',
                    'medio': (getattr(obj, 'medio', '') or '').strip(),
                    'op_nom': (getattr(op, 'first_name', '') or '').strip() + ' ' + (getattr(op, 'last_name', '') or '').strip(),
                    'op_rol': (getattr(op, 'rol_sistema', '') or '').strip(),
                })
            for obj in qs_refrigerios.order_by('-fecha_hora')[:5]:
                p = obj.persona
                op = obj.operador
                actividad.append({
                    'entrega': obj.fecha_hora,
                    'tipo': 'REFRIGERIO',
                    'doc': getattr(p, 'numero_identificacion', '') or '',
                    'nombres': getattr(p, 'nombres', '') or '',
                    'apellidos': getattr(p, 'apellidos', '') or '',
                    'rol': getattr(p, 'tipo_persona', '') or '',
                    'medio': (getattr(obj, 'medio', '') or '').strip(),
                    'op_nom': (getattr(op, 'first_name', '') or '').strip() + ' ' + (getattr(op, 'last_name', '') or '').strip(),
                    'op_rol': (getattr(op, 'rol_sistema', '') or '').strip(),
                })
            for obj in qs_certificados.order_by('-fecha_hora_entrega')[:5]:
                p = obj.persona
                op = obj.operador
                actividad.append({
                    'entrega': obj.fecha_hora_entrega,
                    'tipo': 'CERTIFICADO',
                    'doc': getattr(p, 'numero_identificacion', '') or '',
                    'nombres': getattr(p, 'nombres', '') or '',
                    'apellidos': getattr(p, 'apellidos', '') or '',
                    'rol': getattr(p, 'tipo_persona', '') or '',
                    'medio': (getattr(obj, 'medio', '') or '').strip(),
                    'op_nom': (getattr(op, 'first_name', '') or '').strip() + ' ' + (getattr(op, 'last_name', '') or '').strip(),
                    'op_rol': (getattr(op, 'rol_sistema', '') or '').strip(),
                })
            actividad.sort(key=lambda r: r.get('entrega') or timezone.now(), reverse=True)
            actividad = actividad[:15]
        except Exception:
            actividad = []

        actividad_formateada = []
        for r in actividad:
            f = r.get('entrega')
            if f:
                try: hora = timezone.localtime(f).strftime('%H:%M')
                except Exception: hora = str(f)[11:16]
            else:
                hora = '—'
            op_nom = (r.get('op_nom') or '').strip() or '—'
            op_rol = (r.get('op_rol') or '').strip()
            operador = f"{op_nom} · [{op_rol}]" if op_rol else op_nom
            nombre = f"{r.get('nombres') or ''} {r.get('apellidos') or ''}".strip() or '—'
            actividad_formateada.append({
                'tipo': (r.get('tipo') or '').strip() or '—',
                'hora': hora,
                'doc': (r.get('doc') or '').strip() or '—',
                'nombre': nombre,
                'rol': (r.get('rol') or '').strip() or '—',
                'medio': (r.get('medio') or '').strip() or '—',
                'operador': operador,
            })

        return render(request, 'simple/dashboard.html', {
            'evento': evento,
            'estado_evento': estado_evento,
            'hora_actual': ahora.strftime('%H:%M'),
            'total_personas': total_personas,
            'total_aprendices': total_aprendices,
            'total_instructores': total_instructores,
            'total_invitados': total_invitados,
            'total_organizadores': total_organizadores,
            'total_visitantes': total_visitantes,
            'total_proyectos': total_proyectos,
            'total_instituciones_inscritas': total_instituciones_inscritas,
            'total_programas_unicos': total_programas_unicos,
            'total_fichas_unicas': total_fichas_unicas,
            'total_personas_estructura': total_personas_estructura,
            'personas_estructura_desglose': personas_estructura_desglose,

            'asistentes': asistentes_total,
            'ausentes': ausentes,
            'pct_asistencia': pct_asistencia,
            'asistentes_aprendices': asistentes_aprendices,
            'asistentes_instructores': asistentes_instructores,
            'asistentes_invitados': asistentes_invitados,
            'asistentes_organizadores': asistentes_organizadores,
            'asist_qr': asist_qr,
            'asist_manual': asist_manual,

            'refrigerios_entregados': refrigerios_entregados,
            'refrigerios_pendientes': refrigerios_pendientes,
            'pct_refrigerios': pct_refrigerios,
            'refri_aprendices': refri_aprendices,
            'refri_instructores': refri_instructores,
            'refri_invitados': refri_invitados,
            'refri_organizadores': refri_organizadores,
            'refri_qr': refri_qr,
            'refri_manual': refri_manual,
            'refrigerios_por_tipo': refrigerios_por_tipo,
            'tipos_servicio_activos': tipos_servicio_activos,

            'certificados_entregados': certificados_entregados,
            'certificados_pendientes': certificados_pendientes,
            'pct_certificados': pct_certificados,
            'cert_aprendices': cert_aprendices,
            'cert_instructores': cert_instructores,
            'cert_invitados': cert_invitados,
            'cert_organizadores': cert_organizadores,
            'cert_qr': cert_qr,
            'cert_manual': cert_manual,

            'actividad': actividad_formateada,
        })


# ============================================================
# LISTADOS: COLEGIOS, PROGRAMAS, INSTRUCTORES, INVITADOS (ÚNICOS, SIN REPETICIONES)
# ============================================================
class ListadoUnicosView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, que='colegios', **_ignorado):
        from django.shortcuts import redirect
        from django.http import Http404
        que_normalizado = (que or '').strip().lower()
        evento = _evento_activo()
        ids = request.POST.getlist('ids')
        accion = (request.POST.get('accion') or '').strip()
        eliminar_sencillo = (request.POST.get('eliminar') or '').strip()
        pk_sencillo = None
        try:
            if eliminar_sencillo:
                pk_sencillo = int(eliminar_sencillo)
        except (ValueError, TypeError):
            pk_sencillo = None
        if que_normalizado == 'asistencia':
            qs_total = AsistenciaEvento.objects.all()
            if evento:
                qs_total = qs_total.filter(evento=evento)
            if pk_sencillo:
                qs = qs_total.filter(pk=pk_sencillo)
                n = qs.count()
                qs.delete()
                messages.success(request, f'✅ Se eliminó 1 asistencia.')
            elif accion == 'eliminar' and ids:
                qs = qs_total.filter(pk__in=ids)
                n = qs.count()
                qs.delete()
                messages.success(request, f'✅ Se eliminaron {n} asistencia(s).')
            else:
                messages.warning(request, '⚠ Selecciona asistencias para eliminar.')
            return redirect('simple:listados', que='asistencia')
        if que_normalizado == 'refrigerios':
            svc = _servicio_almuerzo(evento) if evento else None
            qs_total = EntregaServicio.objects.all()
            if evento:
                qs_total = qs_total.filter(evento=evento)
            if svc:
                qs_total = qs_total.filter(tipo_servicio=svc)
            if pk_sencillo:
                qs = qs_total.filter(pk=pk_sencillo)
                qs.delete()
                messages.success(request, f'✅ Se eliminó 1 entrega de refrigerio.')
            elif accion == 'eliminar' and ids:
                qs = qs_total.filter(pk__in=ids)
                n = qs.count()
                qs.delete()
                messages.success(request, f'✅ Se eliminaron {n} entrega(s) de refrigerio.')
            else:
                messages.warning(request, '⚠ Selecciona entregas para eliminar.')
            return redirect('simple:listados', que='refrigerios')
        if que_normalizado == 'certificados':
            qs_total = Certificado.objects.all()
            if evento:
                qs_total = qs_total.filter(evento=evento)
            if pk_sencillo:
                qs = qs_total.filter(pk=pk_sencillo)
                qs.delete()
                messages.success(request, f'✅ Se eliminó 1 certificado entregado.')
            elif accion == 'eliminar' and ids:
                qs = qs_total.filter(pk__in=ids)
                n = qs.count()
                qs.delete()
                messages.success(request, f'✅ Se eliminaron {n} certificado(s) entregado(s).')
            else:
                messages.warning(request, '⚠ Selecciona certificados para eliminar.')
            return redirect('simple:listados', que='certificados')
        raise Http404('Acción no soportada para este listado.')

    def get(self, request, que='colegios', **_ignorado):
        data = None
        titulo = ''
        columnas_especiales = None
        que_normalizado = (que or '').strip().lower()
        evento = _evento_activo()
        if que_normalizado == 'colegios':
            titulo = 'Instituciones Educativas (únicas)'
            data = InstitucionEducativa.objects.order_by('nombre').all()
        elif que_normalizado == 'programas':
            titulo = 'Programas Técnicos (únicos)'
            data = ProgramaTecnico.objects.order_by('nombre').all()
        elif que_normalizado == 'instructores':
            titulo = 'Instructores (únicos)'
            data = _qs_perfiles_o_fallback(Instructor, 'INSTRUCTOR')
        elif que_normalizado == 'invitados':
            titulo = 'Invitados (únicos)'
            data = _qs_perfiles_o_fallback(Invitado, 'INVITADO')
        elif que_normalizado == 'organizadores':
            titulo = 'Organizadores (únicos)'
            data = _qs_perfiles_o_fallback(_Organizador, 'ORGANIZADOR')
        elif que_normalizado == 'visitantes':
            titulo = 'Visitantes (únicos)'
            try:
                from apps.visitantes.models import Visitante as _VisMod
                data = _qs_perfiles_o_fallback(_VisMod, 'VISITANTE')
            except Exception:
                data = _qs_perfiles_o_fallback(None, 'VISITANTE')
        elif que_normalizado == 'proyectos':
            titulo = 'Proyectos registrados'
            data = Proyecto.objects.select_related('institucion', 'programa', 'instructor_responsable__persona').order_by('codigo').all()
        elif que_normalizado == 'aprendices':
            titulo = 'Aprendices por proyecto'
            data = _qs_perfiles_o_fallback(Aprendiz, 'APRENDIZ', extra_order='proyecto__codigo')
        elif que_normalizado in ('asistencia', 'asistencias'):
            titulo = 'Lista de Asistencias'
            qs = AsistenciaEvento.objects.select_related('persona', 'evento', 'operador').order_by('-fecha_hora')
            if evento:
                qs = qs.filter(evento=evento)
            data = qs
            columnas_especiales = 'asistencia'
        elif que_normalizado in ('refrigerios', 'entregas', 'almuerzos'):
            svc = _servicio_almuerzo(evento) if evento else None
            if svc:
                titulo = f'Entregas de {svc.nombre}'
            else:
                titulo = 'Entregas de Refrigerios'
            qs = EntregaServicio.objects.select_related('persona', 'evento', 'operador', 'tipo_servicio').order_by('-fecha_hora')
            if evento:
                qs = qs.filter(evento=evento)
            if svc:
                qs = qs.filter(tipo_servicio=svc)
            data = qs
            columnas_especiales = 'entrega'
        elif que_normalizado in ('certificados', 'certificados_entregados'):
            titulo = 'Certificados Entregados'
            qs = Certificado.objects.select_related('persona', 'evento', 'operador').order_by('-fecha_hora_entrega')
            if evento:
                qs = qs.filter(evento=evento)
            data = qs
            columnas_especiales = 'certificado'
        return render(request, 'simple/listados_unicos.html', {
            'que': que_normalizado, 'titulo': titulo, 'filas': data,
            'columnas_especiales': columnas_especiales,
        })


# ============================================================
# ESCARAPELAS PDF - Individual / Lotes
# ============================================================
class DescargarEscarapelaIndividual(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO', 'OPERATIVO']

    def dispatch(self, request, *args, **kwargs):
        token_url = kwargs.get('token_registro')
        if token_url:
            return super().dispatch(request, *args, **kwargs)
        auth_resp = _solicitar_login_o_token(request, 'registro')
        if auth_resp is not None:
            return auth_resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, persona_id, **_ignorado):
        p = get_object_or_404(Persona, pk=persona_id)
        evento = _evento_activo()
        proyecto = None
        try:
            if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz:
                proyecto = p.perfil_aprendiz.proyecto
        except Exception:
            pass
        buffer = generar_escarapela_individual(p, evento=evento, proyecto=proyecto)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="escarapela_{p.numero_identificacion or p.id}.pdf"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


class DescargarEscarapelasLote(LoginRequiredMixin, View):
    def get(self, request, grupo='todos', **_ignorado):
        evento = _evento_activo()
        queryset = Persona.objects.filter(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO', 'ORGANIZADOR'])
        items = []
        if grupo == 'todos':
            for p in queryset.order_by('tipo_persona', 'apellidos'):
                proy = None
                try:
                    if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz:
                        proy = p.perfil_aprendiz.proyecto
                except Exception:
                    pass
                items.append((p, proy))
        elif grupo == 'aprendices':
            for a in _qs_perfiles_o_fallback(Aprendiz, 'APRENDIZ'):
                _proy = getattr(a, 'proyecto', None) or (a.get('proyecto') if isinstance(a, dict) else None)
                _per = getattr(a, 'persona', None) or (a.get('persona') if isinstance(a, dict) else None)
                if _per:
                    items.append((_per, _proy))
        elif grupo == 'instructores':
            for i in _qs_perfiles_o_fallback(Instructor, 'INSTRUCTOR'):
                _per = getattr(i, 'persona', None) or (i.get('persona') if isinstance(i, dict) else None)
                if _per:
                    items.append((_per, None))
        elif grupo == 'invitados':
            for i in _qs_perfiles_o_fallback(Invitado, 'INVITADO'):
                _per = getattr(i, 'persona', None) or (i.get('persona') if isinstance(i, dict) else None)
                if _per:
                    items.append((_per, None))
        elif grupo == 'organizadores':
            for o in _qs_perfiles_o_fallback(_Organizador, 'ORGANIZADOR'):
                _per = getattr(o, 'persona', None) or (o.get('persona') if isinstance(o, dict) else None)
                if _per:
                    items.append((_per, None))
        elif grupo == 'visitantes':
            try:
                from apps.visitantes.models import Visitante as _VisMod
                _qs_vis = _qs_perfiles_o_fallback(_VisMod, 'VISITANTE')
            except Exception:
                _qs_vis = _qs_perfiles_o_fallback(None, 'VISITANTE')
            for v in _qs_vis:
                _per = getattr(v, 'persona', None) or (v.get('persona') if isinstance(v, dict) else None)
                if _per:
                    items.append((_per, None))
        elif grupo == 'asistentes':
            asistencias = AsistenciaEvento.objects.filter(evento=evento).select_related('persona')
            seen = set()
            for a in asistencias:
                if a.persona_id in seen:
                    continue
                seen.add(a.persona_id)
                proy = None
                try:
                    if hasattr(a.persona, 'perfil_aprendiz') and a.persona.perfil_aprendiz:
                        proy = a.persona.perfil_aprendiz.proyecto
                except Exception:
                    pass
                items.append((a.persona, proy))
        else:
            try:
                pk = int(grupo)
                institucion = get_object_or_404(InstitucionEducativa, pk=pk)
                for proyecto in Proyecto.objects.filter(institucion=institucion).order_by('codigo'):
                    for a in Aprendiz.objects.filter(proyecto=proyecto).select_related('persona'):
                        items.append((a.persona, proyecto))
                    if proyecto.instructor_responsable and proyecto.instructor_responsable.persona:
                        items.append((proyecto.instructor_responsable.persona, proyecto))
                grupo = f'institucion_{pk}'
            except Exception:
                pass

        if not items:
            messages.warning(request, 'No hay personas para generar escarapelas en este grupo.')
            return redirect('simple:listados', que='aprendices')

        buffer = generar_escarapelas_lote(items, evento=evento, nombre_archivo=f'escarapelas_{grupo}.pdf')
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="escarapelas_{grupo}.pdf"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


# ============================================================
# CERTIFICADOS - Formulario de EDICIÓN (previa) y Descarga
# ============================================================
class EditarCertificadoView(LoginRequiredMixin, View):
    def get(self, request, persona_id, tipo='ASISTENCIA', **_ignorado):
        p = get_object_or_404(Persona, pk=persona_id)
        tipo = (tipo or 'ASISTENCIA').upper()
        evento = _evento_activo()
        proyecto = None
        try:
            if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz and p.perfil_aprendiz.proyecto:
                proyecto = p.perfil_aprendiz.proyecto
        except Exception:
            pass
        from datetime import date
        from apps.core.simple_pdf import _reemplazar_plantilla
        plantilla = PLANTILLAS_CERTIFICADO.get(tipo, PLANTILLAS_CERTIFICADO['ASISTENCIA'])
        vars_ = _reemplazar_plantilla(plantilla, p, evento=evento, proyecto=proyecto)
        return render(request, 'simple/editar_certificado.html', {
            'persona': p,
            'tipo': tipo,
            'plantilla': plantilla,
            'vars_': vars_,
            'evento': evento,
            'proyecto': proyecto,
            'fecha_hoy': date.today().strftime('%Y-%m-%d'),
        })

    def post(self, request, persona_id, tipo='ASISTENCIA', **_ignorado):
        p = get_object_or_404(Persona, pk=persona_id)
        tipo = (tipo or 'ASISTENCIA').upper()
        evento = _evento_activo()
        proyecto = None
        try:
            if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz and p.perfil_aprendiz.proyecto:
                proyecto = p.perfil_aprendiz.proyecto
        except Exception:
            pass
        overrides = {
            'NOMBRE_COMPLETO': request.POST.get('NOMBRE_COMPLETO') or None,
            'TIPO_ID': request.POST.get('TIPO_ID') or None,
            'NUMERO_ID': request.POST.get('NUMERO_ID') or None,
            'EVENTO': request.POST.get('EVENTO') or None,
            'LUGAR': request.POST.get('LUGAR') or None,
            'MUNICIPIO': request.POST.get('MUNICIPIO') or None,
            'FECHA_INICIO': request.POST.get('FECHA_INICIO') or None,
            'FECHA_FIN': request.POST.get('FECHA_FIN') or None,
            'FECHA_EMISION': request.POST.get('FECHA_EMISION') or None,
            'ROL': request.POST.get('ROL') or None,
            'NOMBRE_PROYECTO': request.POST.get('NOMBRE_PROYECTO') or None,
            'CODIGO_PROYECTO': request.POST.get('CODIGO_PROYECTO') or None,
            'INSTITUCION': request.POST.get('INSTITUCION') or None,
            'FIRMA_1_NOMBRE': request.POST.get('FIRMA_1_NOMBRE') or None,
            'FIRMA_1_CARGO': request.POST.get('FIRMA_1_CARGO') or None,
            'FIRMA_2_NOMBRE': request.POST.get('FIRMA_2_NOMBRE') or None,
            'FIRMA_2_CARGO': request.POST.get('FIRMA_2_CARGO') or None,
        }
        overrides = {k: v for k, v in overrides.items() if v}

        modo = request.POST.get('accion', 'descargar')
        buffer = generar_certificado_pdf(p, tipo=tipo, evento=evento, proyecto=proyecto, overrides=overrides)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f'{tipo}_{p.numero_identificacion or p.id}.pdf'
        if modo == 'previsualizar':
            resp['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


class DescargarCertificadosLoteView(LoginRequiredMixin, View):
    def get(self, request, tipo='ASISTENCIA', grupo='asistentes', **_ignorado):
        evento = _evento_activo()
        tipo = (tipo or 'ASISTENCIA').upper()
        lista = []
        if grupo == 'asistentes' and evento:
            asistencias = AsistenciaEvento.objects.filter(evento=evento).select_related('persona')
            seen = set()
            for a in asistencias:
                if a.persona_id in seen:
                    continue
                seen.add(a.persona_id)
                proy = None
                try:
                    if hasattr(a.persona, 'perfil_aprendiz') and a.persona.perfil_aprendiz:
                        proy = a.persona.perfil_aprendiz.proyecto
                except Exception:
                    pass
                lista.append((a.persona, proy))
        elif grupo == 'todos':
            for p in Persona.objects.filter(tipo_persona__in=['APRENDIZ', 'INSTRUCTOR', 'INVITADO', 'ORGANIZADOR']).order_by('tipo_persona', 'apellidos'):
                proy = None
                try:
                    if hasattr(p, 'perfil_aprendiz') and p.perfil_aprendiz:
                        proy = p.perfil_aprendiz.proyecto
                except Exception:
                    pass
                lista.append((p, proy))
        elif grupo == 'aprendices':
            for a in _qs_perfiles_o_fallback(Aprendiz, 'APRENDIZ'):
                _proy = getattr(a, 'proyecto', None) or (a.get('proyecto') if isinstance(a, dict) else None)
                _per = getattr(a, 'persona', None) or (a.get('persona') if isinstance(a, dict) else None)
                if _per:
                    lista.append((_per, _proy))
        elif grupo == 'instructores':
            for i in _qs_perfiles_o_fallback(Instructor, 'INSTRUCTOR'):
                _per = getattr(i, 'persona', None) or (i.get('persona') if isinstance(i, dict) else None)
                if _per:
                    lista.append((_per, None))
        elif grupo == 'invitados':
            for i in _qs_perfiles_o_fallback(Invitado, 'INVITADO'):
                _per = getattr(i, 'persona', None) or (i.get('persona') if isinstance(i, dict) else None)
                if _per:
                    lista.append((_per, None))
        elif grupo == 'organizadores':
            for o in _qs_perfiles_o_fallback(_Organizador, 'ORGANIZADOR'):
                _per = getattr(o, 'persona', None) or (o.get('persona') if isinstance(o, dict) else None)
                if _per:
                    lista.append((_per, None))
        elif grupo == 'visitantes':
            try:
                from apps.visitantes.models import Visitante as _VisMod
                _qs_vis = _qs_perfiles_o_fallback(_VisMod, 'VISITANTE')
            except Exception:
                _qs_vis = _qs_perfiles_o_fallback(None, 'VISITANTE')
            for v in _qs_vis:
                _per = getattr(v, 'persona', None) or (v.get('persona') if isinstance(v, dict) else None)
                if _per:
                    lista.append((_per, None))

        if not lista:
            messages.warning(request, 'No hay certificados para generar.')
            return redirect('simple:dashboard')

        buffer = generar_certificados_lote(lista, tipo=tipo, evento=evento)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="certificados_{tipo}_{grupo}.pdf"'
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp


# ============================================================
# FORMULARIO DE REGISTRO RÁPIDO · PERSONAS (Invitados / Instructores / Organizadores)
# ============================================================
class RegistroPersonasPublicView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    template_name = 'simple/registro_personas.html'
    modo = 'registro'

    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        evento = _evento_activo()
        try:
            inicial_ti = TipoIdentificacion.objects.filter(activo=True, codigo='CC').first()
        except Exception:
            inicial_ti = None
        f = RegistroPersonasPublicoForm(initial={'tipo_identificacion': inicial_ti} if inicial_ti else None)
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        base = request.build_absolute_uri('/').rstrip('/')
        url_reg_personas = f"{base}/r/{t_r}/registro/personas/" if t_r else reverse('simple:registro_personas')
        return render(request, self.template_name, {
            'evento': evento,
            'form': f,
            'token_registro': t_r,
            'url_registro_personas': url_reg_personas,
        })

    def post(self, request, **_ignorado):
        evento = _evento_activo()
        form = RegistroPersonasPublicoForm(request.POST or None)
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        base = request.build_absolute_uri('/').rstrip('/')
        url_reg_personas = f"{base}/r/{t_r}/registro/personas/" if t_r else reverse('simple:registro_personas')
        if not form.is_valid():
            return render(request, self.template_name, {
                'evento': evento,
                'form': form,
                'token_registro': t_r,
                'url_registro_personas': url_reg_personas,
            })
        try:
            persona, created, warns = guardar_persona_publica(
                form.cleaned_data,
                creado_por=(request.user if request.user.is_authenticated else None),
            )
        except Exception as err:
            form.add_error(None, f'❌ Error guardando los datos: {err}')
            return render(request, self.template_name, {
                'evento': evento,
                'form': form,
                'token_registro': t_r,
                'url_registro_personas': url_reg_personas,
            })
        for w in warns:
            messages.warning(request, w)
        if created:
            messages.success(request, f'✅ Registro guardado correctamente. ¡Gracias por asistir!')
        else:
            messages.info(request, 'ℹ️ El documento ya estaba registrado. Se actualizaron los datos.')
        if t_r:
            url_gracias = reverse('simple:public_registro_personas_gracias', kwargs={
                'token_registro': t_r, 'pk': persona.pk,
            })
        else:
            url_gracias = reverse('simple:registro_personas_gracias', kwargs={'pk': persona.pk})
        return HttpResponseRedirect(url_gracias)


class RegistroPersonasGraciasView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    template_name = 'simple/registro_personas_gracias.html'

    def dispatch(self, request, *args, **kwargs):
        t_url = kwargs.get('token_registro')
        if not t_url:
            auth_resp = _solicitar_login_o_token(request, 'registro')
            if auth_resp is not None:
                return auth_resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, **kwargs):
        evento = _evento_activo()
        persona = get_object_or_404(Persona, pk=pk)
        t_r = kwargs.get('token_registro') or settings.TOKEN_REGISTRO_PUBLICO or ''
        if t_r:
            url_escarapela = reverse(
                'simple:public_escarapela',
                kwargs={'token_registro': t_r, 'persona_id': persona.pk},
            )
            url_form = reverse('simple:public_registro_personas', kwargs={'token_registro': t_r})
        else:
            url_escarapela = reverse('simple:escarapela_persona', kwargs={'persona_id': persona.pk})
            url_form = reverse('simple:registro_personas')
        rol_display = dict(Persona.TIPOS).get(persona.tipo_persona, persona.tipo_persona)
        rol_pill_cls = {
            'APRENDIZ': 'bg-verde-claro text-white',
            'INSTRUCTOR': 'bg-naranja text-white',
            'INVITADO': 'bg-azul-o text-white',
            'ORGANIZADOR': 'bg-azul text-white',
        }.get(persona.tipo_persona, 'bg-gray-600 text-white')
        return render(request, self.template_name, {
            'evento': evento,
            'persona': persona,
            'rol_display': rol_display,
            'rol_pill_cls': rol_pill_cls,
            'url_escarapela': url_escarapela,
            'url_form': url_form,
            'token_registro': t_r,
        })


class RegistroInvitadosPublicView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    template_name = 'simple/registro_invitados.html'
    modo = 'registro'

    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        evento = _evento_activo()
        try:
            inicial_ti = TipoIdentificacion.objects.filter(activo=True, codigo='CC').first()
        except Exception:
            inicial_ti = None
        f = RegistroInvitadosPublicoForm(
            initial={'tipo_identificacion': inicial_ti, 'tipo_rol': 'INVITADO'} if inicial_ti else {'tipo_rol': 'INVITADO'}
        )
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        base = request.build_absolute_uri('/').rstrip('/')
        url_reg_invitados = f"{base}/r/{t_r}/registro/invitados/" if t_r else reverse('simple:registro_invitados')
        return render(request, self.template_name, {
            'evento': evento,
            'form': f,
            'token_registro': t_r,
            'url_registro_invitados': url_reg_invitados,
        })

    def post(self, request, **_ignorado):
        evento = _evento_activo()
        form = RegistroInvitadosPublicoForm(request.POST or None)
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        base = request.build_absolute_uri('/').rstrip('/')
        url_reg_invitados = f"{base}/r/{t_r}/registro/invitados/" if t_r else reverse('simple:registro_invitados')
        if not form.is_valid():
            return render(request, self.template_name, {
                'evento': evento,
                'form': form,
                'token_registro': t_r,
                'url_registro_invitados': url_reg_invitados,
            })
        datos = dict(form.cleaned_data)
        datos['tipo_rol'] = 'INVITADO'
        try:
            persona, created, warns = guardar_persona_publica(
                datos,
                creado_por=(request.user if request.user.is_authenticated else None),
            )
        except Exception as err:
            form.add_error(None, f'❌ Error guardando los datos: {err}')
            return render(request, self.template_name, {
                'evento': evento,
                'form': form,
                'token_registro': t_r,
                'url_registro_invitados': url_reg_invitados,
            })
        for w in warns:
            messages.warning(request, w)
        if created:
            messages.success(request, f'✅ Invitado registrado correctamente. ¡Gracias por asistir!')
        else:
            messages.info(request, 'ℹ️ El documento del invitado ya estaba registrado. Se actualizaron los datos.')
        if t_r:
            url_gracias = reverse('simple:public_registro_invitados_gracias', kwargs={
                'token_registro': t_r, 'pk': persona.pk,
            })
        else:
            url_gracias = reverse('simple:registro_invitados_gracias', kwargs={'pk': persona.pk})
        return HttpResponseRedirect(url_gracias)


class RegistroInvitadosGraciasView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    template_name = 'simple/registro_invitados_gracias.html'

    def dispatch(self, request, *args, **kwargs):
        t_url = kwargs.get('token_registro')
        if not t_url:
            auth_resp = _solicitar_login_o_token(request, 'registro')
            if auth_resp is not None:
                return auth_resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, **kwargs):
        evento = _evento_activo()
        t_r = kwargs.get('token_registro') or settings.TOKEN_REGISTRO_PUBLICO or ''
        try:
            persona = Persona.objects.get(pk=pk)
        except (Persona.DoesNotExist, ValueError, TypeError):
            persona = None
            no_encontrado = True
        else:
            no_encontrado = False
        if persona is not None and persona.tipo_persona != 'INVITADO':
            no_encontrado = True
        if no_encontrado:
            if t_r:
                url_form = reverse('simple:public_registro_invitados', kwargs={'token_registro': t_r})
            else:
                url_form = reverse('simple:registro_invitados')
            return render(request, 'simple/registro_invitados_gracias.html', {
                'evento': evento,
                'persona': None,
                'no_encontrado': True,
                'url_form': url_form,
                'token_registro': t_r,
            })
        if t_r:
            url_escarapela = reverse(
                'simple:public_escarapela',
                kwargs={'token_registro': t_r, 'persona_id': persona.pk},
            )
            url_form = reverse('simple:public_registro_invitados', kwargs={'token_registro': t_r})
        else:
            url_escarapela = reverse('simple:escarapela_persona', kwargs={'persona_id': persona.pk})
            url_form = reverse('simple:registro_invitados')
        rol_display = dict(Persona.TIPOS).get(persona.tipo_persona, persona.tipo_persona)
        rol_pill_cls = {
            'APRENDIZ': 'bg-verde-claro text-white',
            'INSTRUCTOR': 'bg-naranja text-white',
            'INVITADO': 'bg-azul-o text-white',
            'ORGANIZADOR': 'bg-azul text-white',
        }.get(persona.tipo_persona, 'bg-gray-600 text-white')
        entidad_mostrar = None
        cargo_mostrar = None
        try:
            perfil_inv = persona.perfil_invitado
            if perfil_inv:
                if getattr(perfil_inv, 'entidad', None):
                    entidad_mostrar = str(perfil_inv.entidad).strip() or None
                if getattr(perfil_inv, 'cargo', None):
                    cargo_mostrar = str(perfil_inv.cargo).strip() or None
        except Exception:
            pass
        if not entidad_mostrar:
            try:
                v = getattr(persona, 'entidad_canonica', None)
                if v: entidad_mostrar = v
            except Exception:
                pass
        if not cargo_mostrar:
            try:
                v = getattr(persona, 'cargo_canonico', None)
                if v: cargo_mostrar = v
            except Exception:
                pass
        if not entidad_mostrar:
            try:
                v = getattr(persona, 'entidad', None)
                if v: entidad_mostrar = v
            except Exception:
                pass
        if not cargo_mostrar:
            try:
                v = getattr(persona, 'cargo', None)
                if v: cargo_mostrar = v
            except Exception:
                pass
        if entidad_mostrar:
            try:
                entidad_mostrar = str(entidad_mostrar).strip().upper()
            except Exception:
                pass
        if cargo_mostrar:
            try:
                cargo_mostrar = str(cargo_mostrar).strip().upper()
            except Exception:
                pass
        return render(request, 'simple/registro_invitados_gracias.html', {
            'evento': evento,
            'persona': persona,
            'rol_display': rol_display,
            'rol_pill_cls': rol_pill_cls,
            'url_escarapela': url_escarapela,
            'url_form': url_form,
            'token_registro': t_r,
            'no_encontrado': False,
            'entidad_mostrar': entidad_mostrar,
            'cargo_mostrar': cargo_mostrar,
        })


class RegistroVisitantesPublicView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    template_name = 'simple/registro_visitantes.html'
    modo = 'registro'

    def dispatch(self, request, *args, **kwargs):
        resp = _solicitar_login_o_token(request, 'registro')
        if resp is not None:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **_ignorado):
        evento = _evento_activo()
        try:
            inicial_ti = TipoIdentificacion.objects.filter(activo=True, codigo='CC').first()
        except Exception:
            inicial_ti = None
        f = RegistroVisitantesPublicoForm(
            initial={'tipo_identificacion': inicial_ti, 'tipo_rol': 'VISITANTE'} if inicial_ti else {'tipo_rol': 'VISITANTE'}
        )
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        base = request.build_absolute_uri('/').rstrip('/')
        url_reg_visitantes = f"{base}/r/{t_r}/registro/visitantes/" if t_r else reverse('simple:registro_visitantes')
        return render(request, self.template_name, {
            'evento': evento,
            'form': f,
            'token_registro': t_r,
            'url_registro_visitantes': url_reg_visitantes,
        })

    def post(self, request, **_ignorado):
        evento = _evento_activo()
        form = RegistroVisitantesPublicoForm(request.POST or None)
        t_r = settings.TOKEN_REGISTRO_PUBLICO or ''
        base = request.build_absolute_uri('/').rstrip('/')
        url_reg_visitantes = f"{base}/r/{t_r}/registro/visitantes/" if t_r else reverse('simple:registro_visitantes')
        if not form.is_valid():
            return render(request, self.template_name, {
                'evento': evento,
                'form': form,
                'token_registro': t_r,
                'url_registro_visitantes': url_reg_visitantes,
            })
        datos = dict(form.cleaned_data)
        datos['tipo_rol'] = 'VISITANTE'
        try:
            persona, created, warns = guardar_persona_publica(
                datos,
                creado_por=(request.user if request.user.is_authenticated else None),
            )
        except Exception as err:
            form.add_error(None, f'❌ Error guardando los datos: {err}')
            return render(request, self.template_name, {
                'evento': evento,
                'form': form,
                'token_registro': t_r,
                'url_registro_visitantes': url_reg_visitantes,
            })
        for w in warns:
            messages.warning(request, w)
        if created:
            messages.success(request, f'✅ Visitante registrado correctamente. ¡Gracias por asistir!')
        else:
            messages.info(request, 'ℹ️ El documento del visitante ya estaba registrado. Se actualizaron los datos.')
        if t_r:
            url_gracias = reverse('simple:public_registro_visitantes_gracias', kwargs={
                'token_registro': t_r, 'pk': persona.pk,
            })
        else:
            url_gracias = reverse('simple:registro_visitantes_gracias', kwargs={'pk': persona.pk})
        return HttpResponseRedirect(url_gracias)


class RegistroVisitantesGraciasView(View):
    roles_requeridos = ['ADMINISTRADOR', 'REGISTRO']
    template_name = 'simple/registro_visitantes_gracias.html'

    def dispatch(self, request, *args, **kwargs):
        t_url = kwargs.get('token_registro')
        if not t_url:
            auth_resp = _solicitar_login_o_token(request, 'registro')
            if auth_resp is not None:
                return auth_resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, **kwargs):
        evento = _evento_activo()
        t_r = kwargs.get('token_registro') or settings.TOKEN_REGISTRO_PUBLICO or ''
        try:
            persona = Persona.objects.get(pk=pk)
        except (Persona.DoesNotExist, ValueError, TypeError):
            persona = None
            no_encontrado = True
        else:
            no_encontrado = False
        if persona is not None and persona.tipo_persona != 'VISITANTE':
            no_encontrado = True
        if no_encontrado:
            if t_r:
                url_form = reverse('simple:public_registro_visitantes', kwargs={'token_registro': t_r})
            else:
                url_form = reverse('simple:registro_visitantes')
            return render(request, 'simple/registro_visitantes_gracias.html', {
                'evento': evento,
                'persona': None,
                'no_encontrado': True,
                'url_form': url_form,
                'token_registro': t_r,
            })
        if t_r:
            url_escarapela = reverse(
                'simple:public_escarapela',
                kwargs={'token_registro': t_r, 'persona_id': persona.pk},
            )
            url_form = reverse('simple:public_registro_visitantes', kwargs={'token_registro': t_r})
        else:
            url_escarapela = reverse('simple:escarapela_persona', kwargs={'persona_id': persona.pk})
            url_form = reverse('simple:registro_visitantes')
        rol_display = dict(Persona.TIPOS).get(persona.tipo_persona, persona.tipo_persona)
        rol_pill_cls = {
            'APRENDIZ': 'bg-verde-claro text-white',
            'INSTRUCTOR': 'bg-naranja text-white',
            'INVITADO': 'bg-azul-o text-white',
            'ORGANIZADOR': 'bg-azul text-white',
            'VISITANTE': 'text-white',
        }.get(persona.tipo_persona, 'bg-gray-600 text-white')
        entidad_mostrar = None
        cargo_mostrar = None
        try:
            perfil_vis = persona.perfil_visitante
            if perfil_vis:
                if getattr(perfil_vis, 'entidad', None):
                    entidad_mostrar = str(perfil_vis.entidad).strip() or None
                if getattr(perfil_vis, 'cargo', None):
                    cargo_mostrar = str(perfil_vis.cargo).strip() or None
        except Exception:
            pass
        if not entidad_mostrar:
            try:
                v = getattr(persona, 'entidad_canonica', None)
                if v: entidad_mostrar = v
            except Exception:
                pass
        if not cargo_mostrar:
            try:
                v = getattr(persona, 'cargo_canonico', None)
                if v: cargo_mostrar = v
            except Exception:
                pass
        if not entidad_mostrar:
            try:
                v = getattr(persona, 'entidad', None)
                if v: entidad_mostrar = v
            except Exception:
                pass
        if not cargo_mostrar:
            try:
                v = getattr(persona, 'cargo', None)
                if v: cargo_mostrar = v
            except Exception:
                pass
        if entidad_mostrar:
            try:
                entidad_mostrar = str(entidad_mostrar).strip().upper()
            except Exception:
                pass
        if cargo_mostrar:
            try:
                cargo_mostrar = str(cargo_mostrar).strip().upper()
            except Exception:
                pass
        return render(request, 'simple/registro_visitantes_gracias.html', {
            'evento': evento,
            'persona': persona,
            'rol_display': rol_display,
            'rol_pill_cls': rol_pill_cls,
            'url_escarapela': url_escarapela,
            'url_form': url_form,
            'token_registro': t_r,
            'no_encontrado': False,
            'entidad_mostrar': entidad_mostrar,
            'cargo_mostrar': cargo_mostrar,
        })


TIPOS_IMPORTACION_LABELS = {
    'instituciones': '🏫 Instituciones Educativas',
    'programas': '📚 Programas Técnicos',
    'instructores': '👨‍🏫 Instructores',
    'fichas': '📋 Fichas (7 dígitos)',
    'proyectos': '🚀 Proyectos Productivos',
    'participantes': '👥 Participantes (Personas)',
}


class ImportadorExcelView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR']
    template_name = 'simple/importador_excel.html'
    paso = None

    def get(self, request, **_):
        ctx = {
            'tipos_importacion': [(t, TIPOS_IMPORTACION_LABELS.get(t, t)) for t in TIPOS_IMPORTACION],
            'tipo_seleccionado': request.GET.get('tipo', 'instituciones'),
            'vista': None,
            'resultados': None,
            'estadisticas': None,
            'estadisticas_json': {'VALIDO':0,'ADVERTENCIA':0,'DUPLICADO':0,'ERROR':0,'TOTAL':0},
            'archivo_nombre': '',
        }
        return render(request, self.template_name, ctx)

    def post(self, request, **_):
        accion = request.POST.get('accion', 'validar')
        tipo_importacion = (request.POST.get('tipo_importacion') or '').strip()
        archivo = request.FILES.get('archivo_excel')

        if tipo_importacion not in TIPOS_IMPORTACION:
            messages.error(request, f'Tipo de importación no válido: {tipo_importacion}')
            return redirect('simple:importador_excel')

        if accion == 'validar':
            if not archivo:
                messages.error(request, 'Debe seleccionar un archivo Excel (.xlsx).')
                return redirect(f"{reverse('simple:importador_excel')}?tipo={tipo_importacion}")

            try:
                resultados = ImportacionExcelService.validar(archivo, tipo_importacion)
            except Exception as e:
                messages.error(request, f'Error leyendo el archivo: {e}')
                return redirect(f"{reverse('simple:importador_excel')}?tipo={tipo_importacion}")

            preview = ImportacionExcelService.preview(request, resultados)
            serializados = ImportacionExcelService._serializar_para_confirmar(resultados)
            ctx = {
                'tipos_importacion': [(t, TIPOS_IMPORTACION_LABELS.get(t, t)) for t in TIPOS_IMPORTACION],
                'tipo_seleccionado': tipo_importacion,
                'vista': 'preview',
                'resultados': preview['resultados'],
                'estadisticas': preview['estadisticas'],
                'estadisticas_json': {
                    'VALIDO': preview['estadisticas'].get(CLASIFICACION_VALIDO, 0),
                    'ADVERTENCIA': preview['estadisticas'].get(CLASIFICACION_ADVERTENCIA, 0),
                    'DUPLICADO': preview['estadisticas'].get(CLASIFICACION_DUPLICADO, 0),
                    'ERROR': preview['estadisticas'].get(CLASIFICACION_ERROR, 0),
                    'TOTAL': preview['estadisticas'].get('TOTAL', 0),
                },
                'archivo_nombre': (archivo.name or 'archivo.xlsx')[:80],
                'resultados_serializados_payload': serializados,
                'clases_estado': {
                    CLASIFICACION_VALIDO: 'success',
                    CLASIFICACION_ADVERTENCIA: 'warning',
                    CLASIFICACION_DUPLICADO: 'info',
                    CLASIFICACION_ERROR: 'danger',
                },
            }
            # Guardar payload en sesion (lado servidor Railway DB, sin limite 4KB)
            session_key = f'imp_res_{tipo_importacion}'
            try:
                request.session[session_key] = serializados
                request.session.modified = True
            except Exception:
                pass
            resp = render(request, self.template_name, ctx)
            try:
                resp.delete_cookie(f'_imp_{tipo_importacion}')
            except Exception:
                pass
            return resp

        if accion == 'confirmar':
            import base64
            import json
            import zlib
            session_key = f'imp_res_{tipo_importacion}'
            # PRIORIDAD 1: sesion lado servidor (Railway DB)
            cookie = request.session.get(session_key, '') or ''
            # PRIORIDAD 2: fallback hidden input enviado desde el preview (payload incrustado en HTML)
            if not cookie:
                cookie = (request.POST.get('_imp_payload') or '').strip()
            if not cookie:
                messages.error(request, 'Sesión de importación expiró o no se encontró. Suba el archivo nuevamente.')
                return redirect(f"{reverse('simple:importador_excel')}?tipo={tipo_importacion}")

            try:
                compressed_b64 = cookie
                compressed_bytes = base64.urlsafe_b64decode(compressed_b64.encode('utf-8'))
                json_bytes = zlib.decompress(compressed_bytes)
                resultados_serializados = json.loads(json_bytes.decode('utf-8'))
            except Exception as e:
                messages.error(request, f'No se pudo restaurar el preview: {e}. Vuelva a subir el archivo.')
                return redirect(f"{reverse('simple:importador_excel')}?tipo={tipo_importacion}")

            try:
                with transaction.atomic():
                    resumen = ImportacionExcelService.confirmar(request, tipo_importacion, resultados_serializados)
            except Exception as e:
                messages.error(request, f'Error guardando datos: {e}')
                return redirect(f"{reverse('simple:importador_excel')}?tipo={tipo_importacion}")

            # Limpiar sesion despues de confirmar OK (liberar memoria)
            try:
                if session_key in request.session:
                    del request.session[session_key]
                    request.session.modified = True
            except Exception:
                pass

            filas = resumen.get('filas_procesadas', 0)
            detalle = resumen.get('detalle', [])
            creados = sum(1 for d in detalle if d.get('accion') == 'CREATE')
            actualizados = sum(1 for d in detalle if d.get('accion') == 'UPDATE')
            messages.success(
                request,
                f'✅ Importación completada: {filas} filas procesadas · {creados} nuevos · {actualizados} actualizados.',
            )
            return redirect(f"{reverse('simple:importador_excel')}?tipo={tipo_importacion}")

        messages.error(request, 'Acción no reconocida.')
        return redirect('simple:importador_excel')


# ============================================================
# GESTIÓN DE USUARIOS — solo ADMINISTRADOR (fuera de Django Admin)
# ============================================================
_ROL_STYLES = {
    'ADMINISTRADOR': 'bg-red-600 text-white',
    'REGISTRO': 'bg-verde text-white',
    'GERENTE': 'bg-purpura text-white',
    'OPERADOR_ASISTENCIA': 'bg-verde-claro text-white',
    'OPERADOR_REFRIGERIO': 'bg-naranja text-white',
    'OPERADOR_CERTIFICADO': 'bg-azul-o text-white',
    'CONSULTA': 'bg-gris text-white',
}
_ROL_ICON = {
    'ADMINISTRADOR': '🛡',
    'REGISTRO': '📝',
    'GERENTE': '📊',
    'OPERADOR_ASISTENCIA': '✅',
    'OPERADOR_REFRIGERIO': '🍱',
    'OPERADOR_CERTIFICADO': '📜',
    'CONSULTA': '🔍',
}


class GestionUsuariosView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR']
    template_name = 'simple/gestion_usuarios.html'

    def get(self, request, **_):
        Usu = _UsuarioSistema
        qs = Usu.objects.order_by('-activo', 'rol_sistema', 'apellidos', 'nombres')
        filtro_rol = (request.GET.get('rol') or '').strip().upper()
        filtro_texto = (request.GET.get('q') or '').strip()
        if filtro_rol:
            qs = qs.filter(rol_sistema=filtro_rol)
        if filtro_texto:
            qs = qs.filter(
                _models_django.Q(username__icontains=filtro_texto)
                | _models_django.Q(nombres__icontains=filtro_texto)
                | _models_django.Q(apellidos__icontains=filtro_texto)
                | _models_django.Q(email__icontains=filtro_texto)
            )
        usuarios = list(qs)
        total = _UsuarioSistema.objects.count()
        activos = _UsuarioSistema.objects.filter(activo=True).count()
        inactivos = max(total - activos, 0)
        conteo_por_rol = {}
        for r, _ in (_UsuarioSistema.ROLES_SISTEMA if hasattr(_UsuarioSistema, 'ROLES_SISTEMA') else []):
            conteo_por_rol[r] = _UsuarioSistema.objects.filter(rol_sistema=r).count()
        roles_labels = dict(_UsuarioSistema.ROLES_SISTEMA if hasattr(_UsuarioSistema, 'ROLES_SISTEMA') else [])
        roles_opts_base = [('', 'Todos los roles')] + list(
            (_UsuarioSistema.ROLES_SISTEMA if hasattr(_UsuarioSistema, 'ROLES_SISTEMA') else [])
        )
        roles_opts_con_conteo = []
        for codigo, label in roles_opts_base:
            if codigo:
                roles_opts_con_conteo.append((codigo, label, conteo_por_rol.get(codigo, 0)))
        ctx = {
            'usuarios': usuarios,
            'total': total,
            'activos': activos,
            'inactivos': inactivos,
            'conteo_por_rol': conteo_por_rol,
            'roles_labels': roles_labels,
            'roles_opts': roles_opts_base,
            'roles_opts_con_conteo': roles_opts_con_conteo,
            'filtro_rol': filtro_rol,
            'filtro_texto': filtro_texto,
            'rol_styles': _ROL_STYLES,
            'rol_icon': _ROL_ICON,
        }
        return render(request, self.template_name, ctx)


class CrearEditarUsuarioView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR']
    template_name = 'simple/form_usuario.html'

    def _get_usuario(self, pk):
        if pk:
            return get_object_or_404(_UsuarioSistema, pk=pk)
        return None

    def get(self, request, pk=None, **_):
        usuario = self._get_usuario(pk)
        form = UsuarioGestionForm(instance=usuario)
        return render(request, self.template_name, {
            'form': form,
            'usuario': usuario,
            'es_nuevo': not usuario,
        })

    def post(self, request, pk=None, **_):
        usuario = self._get_usuario(pk)
        form = UsuarioGestionForm(request.POST or None, instance=usuario)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user_guardado = form.save(commit=True)
                    pwd_generada = getattr(user_guardado, '_password_generada', None) or form.cleaned_data.get('_password_generada')
            except Exception as e:
                form.add_error(None, f'❌ Error guardando el usuario: {e}')
                return render(request, self.template_name, {
                    'form': form, 'usuario': usuario, 'es_nuevo': not usuario,
                })
            if usuario:
                if pwd_generada:
                    messages.success(
                        request,
                        f'✅ Usuario actualizado: @{user_guardado.username} · 🔐 <b>NUEVA Contraseña</b>: <span class="badge text-bg-success px-3 py-2" style="font-size:1.02rem;">{pwd_generada}</span> · <b class="text-danger">CÓPIALA y PÁSALA a la persona</b>'
                    )
                else:
                    messages.success(request, f'✅ Usuario actualizado correctamente: @{user_guardado.username}')
            else:
                msgs = [f'✅ Usuario creado correctamente: @{user_guardado.username}']
                if pwd_generada:
                    msgs.append(f'🔐 Usuario: <b>{user_guardado.username}</b> | Password: <b class="text-sena">{pwd_generada}</b>')
                    messages.success(request, ' · '.join(msgs))
                else:
                    messages.success(request, msgs[0])
            return redirect('simple:gestion_usuarios')
        return render(request, self.template_name, {
            'form': form, 'usuario': usuario, 'es_nuevo': not usuario,
        })


class ToggleUsuarioActivoView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR']

    def post(self, request, pk, **_):
        u = get_object_or_404(_UsuarioSistema, pk=pk)
        if u.pk == getattr(request.user, 'pk', None):
            messages.warning(request, '⚠ No puedes desactivarte a ti mismo.')
            return redirect('simple:gestion_usuarios')
        u.activo = not u.activo
        u.is_active = u.activo
        u.save(update_fields=['activo', 'is_active'])
        if u.activo:
            messages.success(request, f'✅ Usuario @{u.username} ACTIVADO.')
        else:
            messages.warning(request, f'⚠ Usuario @{u.username} INACTIVADO (no podrá iniciar sesión).')
        return redirect('simple:gestion_usuarios')


class ResetPasswordUsuarioView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles_requeridos = ['ADMINISTRADOR']
    template_name = 'simple/reset_password_usuario.html'

    def get(self, request, pk, **_):
        u = get_object_or_404(_UsuarioSistema, pk=pk)
        form = ResetPasswordUsuarioForm()
        return render(request, self.template_name, {'form': form, 'usuario': u})

    def post(self, request, pk, **_):
        u = get_object_or_404(_UsuarioSistema, pk=pk)
        form = ResetPasswordUsuarioForm(request.POST or None)
        if form.is_valid():
            pwd = form.cleaned_data['_password_generada']
            u.set_password(pwd)
            u.save(update_fields=['password'])
            messages.success(
                request,
                f'🔐 Contraseña reseteada para <b>@{u.username}</b> · <b>Nueva contraseña</b>: <span class="badge text-bg-success px-3 py-2" style="font-size:1.02rem;">{pwd}</span>'
            )
            return redirect('simple:gestion_usuarios')
        return render(request, self.template_name, {'form': form, 'usuario': u})
