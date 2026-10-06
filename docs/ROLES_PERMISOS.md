# SISTEMA SENA FERIA 2026 — MATRIZ COMPLETA DE ROLES Y PERMISOS

---

## ÍNDICE

1. [Clasificación de Roles](#1-clasificación-de-roles)
2. [Códigos de Permisos](#2-códigos-de-permisos)
3. [MATRIZ: Roles de Acceso del Sistema vs Módulos](#3-matriz-roles-de-acceso-del-sistema-vs-módulos)
4. [MATRIZ: Roles del Evento (Participantes) vs Permisos Públicos](#4-matriz-roles-del-evento-participantes-vs-permisos-públicos)
5. [Arquitectura de Autenticación Django — Groups + Permissions](#5-arquitectura-de-autenticación-django--groups--permissions)
6. [Protección de URLs, Vistas, POST y AJAX](#6-protección-de-urls-vistas-post-y-ajax)
7. [Redirección Post-Login según Rol](#7-redirección-post-login-según-rol)
8. [Prueba Crítica de Permisos (Esperado: HTTP 403)](#8-prueba-crítica-de-permisos-esperado-http-403)
9. [Configuración en settings.py y Custom Backend](#9-configuración-en-settingspy-y-custom-backend)

---

## 1. Clasificación de Roles

### 1.1 ROLES DE ACCESO DEL SISTEMA (Usuarios Internos)

| Nombre del Rol            | Código Interno         | Descripción                                                                 |
|---------------------------|------------------------|-----------------------------------------------------------------------------|
| ADMINISTRADOR             | `ADMINISTRADOR`        | Control total del sistema. Acceso a todos los módulos y configuraciones.   |
| REGISTRO                  | `REGISTRO`             | Gestión de participantes, inscripciones, datos maestros pre-evento.        |
| OPERADOR_ASISTENCIA       | `OPERADOR_ASISTENCIA`  | Registro de ingreso/salida, consulta y marcación de asistencia en puerta.  |
| OPERADOR_REFRIGERIO       | `OPERADOR_REFRIGERIO`  | Control de entrega de refrigerios / refrigerios consumidos.                |
| OPERADOR_CERTIFICADO      | `OPERADOR_CERTIFICADO` | Generación, validación y emisión de certificados de asistencia.            |
| CONSULTA                  | `CONSULTA`             | Perfil de solo lectura para direccionamiento / auditoría interna.          |

### 1.2 ROLES DEL EVENTO (Participantes — Distintos de Roles Sistema)

| Nombre del Rol Evento   | Código Interno     | Descripción                                                              |
|-------------------------|--------------------|--------------------------------------------------------------------------|
| APRENDIZ                | `APRENDIZ`         | Estudiante SENA que presenta proyecto o asiste como asistente.           |
| INSTRUCTOR              | `INSTRUCTOR`       | Funcionario SENA, tutor de proyecto o expositor.                         |
| INVITADO                | `INVITADO`         | Persona externa (empresario, autoridad, público general).                |
| ORGANIZADOR             | `ORGANIZADOR`      | Personal logístico/comité que coordina actividades durante la feria.     |

> **CRÍTICO**: Los `Roles Evento` NO otorgan acceso al panel administrativo del sistema.
> Son atributos de la entidad `Participante/Persona` para clasificación, refrigerio,
> tipo de escarapela y elegibilidad de certificado. El ingreso al panel requiere
> además pertenecer a uno de los 6 "Roles de Acceso del Sistema" (Group Django).

---

## 2. Códigos de Permisos

| Código | Tipo de Permiso       | Equivalente Django `codename`        |
|--------|-----------------------|--------------------------------------|
| **C**  | Crear / Registrar     | `add_<modelo>`                       |
| **R**  | Leer / Consultar / Ver| `view_<modelo>`                      |
| **U**  | Actualizar / Editar   | `change_<modelo>`                    |
| **D**  | Eliminar / Anular     | `delete_<modelo>`                    |
| `—`    | Sin Acceso            | Sin permiso asignado → HTTP 403      |

---

## 3. MATRIZ: Roles de Acceso del Sistema vs Módulos

Leyenda: **C**=Crear, **R**=Leer, **U**=Actualizar, **D**=Eliminar, `—`=Sin Acceso

| MÓDULO                          | ADMINISTRADOR | REGISTRO | OPERADOR_ASISTENCIA | OPERADOR_REFRIGERIO | OPERADOR_CERTIFICADO | CONSULTA |
|---------------------------------|:-------------:|:--------:|:-------------------:|:-------------------:|:--------------------:|:--------:|
| **1. Dashboard**                |    C R U D    |   R —    |       R —           |       R —           |        R —           |   R —    |
| **2. Eventos**                  |    C R U D    |  C R U   |       R —           |       R —           |        R —           |   R —    |
| **3. Usuarios / Permisos**      |    C R U D    |   — —    |       — —           |       — —           |        — —           |   R —    |
| **4. Instituciones**            |    C R U D    |  C R U   |       R —           |       R —           |        R —           |   R —    |
| **5. Programas (Formación)**    |    C R U D    |  C R U   |       R —           |       R —           |        R —           |   R —    |
| **6. Instructores**             |    C R U D    |  C R U   |       R —           |       R —           |        R —           |   R —    |
| **7. Proyectos**                |    C R U D    |  C R U D |       R —           |       — —           |        R —           |   R —    |
| **8. Participantes / Personas** |    C R U D    |  C R U D |       R U           |       R —           |        R —           |   R —    |
| **9. Invitados**                |    C R U D    |  C R U D |       R U           |       R —           |        R —           |   R —    |
| **10. Escarapelas PDF**         |    C R U D    |   R C    |       R C           |       — —           |        R —           |   R —    |
| **11. Ingreso / Asistencia**    |    C R U D    |   R —    |     C R U D         |       R —           |        R U           |   R —    |
| **12. Refrigerios**             |    C R U D    |   R —    |       R —           |     C R U D         |        — —           |   R —    |
| **13. Certificados**            |    C R U D    |   R —    |       R —           |       — —           |      C R U D         |   R —    |
| **14. Reportes Excel / PDF**    |    C R U D    |   R C    |       R C           |       R C           |        R C           |   R C    |
| **15. Auditoría (logs)**        |    R — — —    |   R —    |       — —           |       — —           |        — —           |   R —    |
| **16. Configuración del Sistema**|   C R U D    |   — —    |       — —           |       — —           |        — —           |   — —    |
| **17. Importación Excel**       |    C R — —    |  C R —   |       — —           |       — —           |        — —           |   — —    |
| **18. Búsqueda Rápida (global)**|     R         |    R     |         R           |         R           |          R           |    R     |
| **19. Verificación Pública Certificados**| R    |   R      |       R             |       —             |        R             |   R      |

---

## 4. MATRIZ: Roles del Evento (Participantes) vs Permisos Públicos

Permisos en portales públicos / escaneo QR / consulta pública SIN login.

| ACCIÓN PÚBLICA / CARACTERÍSTICA         | APRENDIZ | INSTRUCTOR | INVITADO | ORGANIZADOR |
|-----------------------------------------|:--------:|:----------:|:--------:|:-----------:|
| Consulta pública de certificado (QR)    |    SÍ    |     SÍ     |    SÍ    |     SÍ      |
| Recibe refrigerio                       |    SÍ    |     SÍ     |  COND*   |     SÍ      |
| Imprime escarapela PDF (individual)     |    SÍ    |     SÍ     |    SÍ    |     SÍ      |
| Elegible certificado asistencia ≥80%    |    SÍ    |     SÍ     |    NO    |     SÍ      |
| Ajuste tipo escarapela (color/logo)     |  AZUL    |   VERDE    | AMARILLO |   ROJO      |
| Registro ingreso (puerta)               |    SÍ    |     SÍ     |    SÍ    |     SÍ      |
| Registro salida (puerta)                |    SÍ    |     SÍ     |    SÍ    |     SÍ      |
| Validación de proyecto expuesto         |    SÍ    |     SÍ     |    —     |     SÍ      |

> *`COND*` = Invitado recibe refrigerio solo si la inscripción incluye alimentación
> (campo `recibe_refrigerio` en el registro de invitado).

---

## 5. Arquitectura de Autenticación Django — Groups + Permissions

### 5.1 Estructura Recomendada

```
📦 Proyecto Django SENA Feria
├── apps/
│   └── seguridad/                ← Módulo de autenticación y autorización
│       ├── models.py             ← Profile (OneToOne User), LogAuditoria
│       ├── management/
│       │   └── commands/
│       │       └── crear_roles_iniciales.py  ← Seed de Groups y Permissions
│       ├── decorators.py         ← @role_required, @ajax_login_required
│       ├── mixins.py             ← RoleRequiredMixin, AjaxPermissionRequiredMixin
│       ├── backends.py           ← CustomAuthBackend (grupos + permisos)
│       ├── signals.py            ← Crear Profile al crear User
│       └── views.py              ← Login, Logout, Redirect post-login
└── settings.py                   ← AUTH_USER_MODEL, LOGIN_URL, REDIRECT_LOGIC
```

### 5.2 Comando de Inicialización (`crear_roles_iniciales.py`)

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLES_SISTEMA = {
    "ADMINISTRADOR": ["todos"],
    "REGISTRO": [
        "view_dashboard",
        "add_evento", "change_evento", "view_evento",
        "add_institucion", "change_institucion", "view_institucion",
        "add_programa", "change_programa", "view_programa",
        "add_instructor", "change_instructor", "view_instructor",
        "add_proyecto", "change_proyecto", "delete_proyecto", "view_proyecto",
        "add_participante", "change_participante", "delete_participante", "view_participante",
        "add_invitado", "change_invitado", "delete_invitado", "view_invitado",
        "add_escarapela", "view_escarapela",
        "view_asistencia",
        "view_refrigerio",
        "view_certificado",
        "view_reporte", "add_reporte",
        "view_auditoria",
        "add_importacion", "view_importacion",
        "busqueda_rapida",
        "verificacion_publica",
    ],
    "OPERADOR_ASISTENCIA": [
        "view_dashboard",
        "view_evento", "view_institucion", "view_programa", "view_instructor",
        "view_proyecto", "view_participante", "change_participante",
        "view_invitado", "change_invitado",
        "view_escarapela", "add_escarapela",
        "add_asistencia", "change_asistencia", "delete_asistencia", "view_asistencia",
        "view_refrigerio",
        "view_certificado", "change_certificado",
        "view_reporte", "add_reporte",
        "busqueda_rapida",
        "verificacion_publica",
    ],
    "OPERADOR_REFRIGERIO": [
        "view_dashboard",
        "view_evento", "view_institucion", "view_programa", "view_instructor",
        "view_participante", "view_invitado",
        "view_asistencia",
        "add_refrigerio", "change_refrigerio", "delete_refrigerio", "view_refrigerio",
        "view_reporte", "add_reporte",
        "busqueda_rapida",
    ],
    "OPERADOR_CERTIFICADO": [
        "view_dashboard",
        "view_evento", "view_institucion", "view_programa", "view_instructor",
        "view_proyecto", "view_participante", "view_invitado", "view_escarapela",
        "view_asistencia", "change_asistencia",
        "add_certificado", "change_certificado", "delete_certificado", "view_certificado",
        "view_reporte", "add_reporte",
        "busqueda_rapida",
        "verificacion_publica",
    ],
    "CONSULTA": [
        "view_dashboard",
        "view_evento", "view_institucion", "view_programa", "view_instructor",
        "view_proyecto", "view_participante", "view_invitado", "view_escarapela",
        "view_asistencia", "view_refrigerio", "view_certificado",
        "view_reporte", "add_reporte",
        "view_auditoria",
        "busqueda_rapida",
        "verificacion_publica",
    ],
}

class Command(BaseCommand):
    help = "Crea los 6 roles de sistema y asigna permisos por Group"

    def handle(self, *args, **options):
        for nombre_rol, permisos_rol in ROLES_SISTEMA.items():
            grupo, _ = Group.objects.get_or_create(name=nombre_rol)
            grupo.permissions.clear()

            if "todos" in permisos_rol:
                todos = Permission.objects.all()
                grupo.permissions.add(*todos)
            else:
                for codename in permisos_rol:
                    try:
                        permiso = Permission.objects.get(codename=codename)
                        grupo.permissions.add(permiso)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"Permiso no encontrado: {codename}")
                        )
            self.stdout.write(self.style.SUCCESS(f"OK → Grupo: {nombre_rol}"))
```

> **Ejecución**: `python manage.py crear_roles_iniciales` (una sola vez durante despliegue).

### 5.3 Modelo Profile Extendido

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

ROLES_EVENTO = (
    ("APRENDIZ", "Aprendiz"),
    ("INSTRUCTOR", "Instructor"),
    ("INVITADO", "Invitado"),
    ("ORGANIZADOR", "Organizador"),
)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    rol_evento = models.CharField(max_length=20, choices=ROLES_EVENTO, blank=True, null=True)
    documento = models.CharField(max_length=30, unique=True, db_index=True)
    telefono = models.CharField(max_length=20, blank=True)
    institucion = models.ForeignKey("core.Institucion", on_delete=models.SET_NULL, null=True, blank=True)
    programa = models.ForeignKey("core.Programa", on_delete=models.SET_NULL, null=True, blank=True)
    fecha_ultimo_acceso = models.DateTimeField(null=True, blank=True)
    ip_ultimo_acceso = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Perfil Usuario"
        verbose_name_plural = "Perfiles Usuarios"

    def __str__(self):
        return f"{self.user.username} - {self.user.groups.first() or 'SIN GRUPO'}"

    @property
    def rol_sistema(self):
        g = self.user.groups.first()
        return g.name if g else "SIN_ROL"

@receiver(post_save, sender=User)
def crear_o_actualizar_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        if not hasattr(instance, "profile"):
            Profile.objects.get_or_create(user=instance)
```

---

## 6. Protección de URLs, Vistas, POST y AJAX

### 6.1 Mixins Reutilizables (`seguridad/mixins.py`)

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect

class RoleRequiredMixin(LoginRequiredMixin):
    """
    Restringe vista a usuarios que pertenezcan a AL MENOS UNO de los grupos listados.
    Si no tiene grupo → HTTP 403.
    Ejemplo: role_required = ["ADMINISTRADOR", "REGISTRO"]
    """
    role_required = None
    raise_exception = True
    permission_denied_message = "403 - No tiene rol autorizado para esta acción."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.role_required:
            grupos_usuario = set(request.user.groups.values_list("name", flat=True))
            if not grupos_usuario.intersection(set(self.role_required)):
                return HttpResponseForbidden(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


class AjaxPermissionRequiredMixin(PermissionRequiredMixin):
    """
    Devuelve JSON { "error": "...", "codigo": 403 } en vez de redirección HTML.
    Obligatorio para todas las vistas consumidas por fetch() / $.ajax().
    """
    def handle_no_permission(self):
        if self.raise_exception or self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "ok": False,
                "codigo": 403,
                "error": "Permiso insuficiente (HTTP 403). Consulte administrador."
            }, status=403)
        return super().handle_no_permission()
```

### 6.2 Decoradores para FBV (Function-Based Views) (`seguridad/decorators.py`)

```python
from functools import wraps
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, permission_required

def role_required(roles, raise_403=True):
    """
    @role_required(["ADMINISTRADOR", "REGISTRO"])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"ok":False,"codigo":401,"error":"Login requerido"}, status=401) \
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest" \
                    else redirect("/login/?next=" + request.path)
            grupos = set(request.user.groups.values_list("name", flat=True))
            if not set(roles).intersection(grupos):
                return JsonResponse({"ok":False,"codigo":403,"error":"Rol no autorizado"}, status=403) \
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest" \
                    else HttpResponseForbidden("403 - Rol no autorizado")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def ajax_login_required(view_func):
    """
    Evita redirección HTML al login en endpoints AJAX → responde JSON 401.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                "ok": False,
                "codigo": 401,
                "error": "Sesión expirada o usuario no autenticado."
            }, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped
```

### 6.3 Ejemplos de Vistas Protegidas

#### a) Vista basada en Clase (Dashboard Admin)
```python
from django.views.generic import TemplateView
from seguridad.mixins import RoleRequiredMixin

class DashboardAdminView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/admin.html"
    role_required = ["ADMINISTRADOR", "REGISTRO", "CONSULTA",
                     "OPERADOR_ASISTENCIA", "OPERADOR_REFRIGERIO", "OPERADOR_CERTIFICADO"]
```

#### b) Vista AJAX POST (marcar refrigerio)
```python
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from seguridad.decorators import ajax_login_required, role_required
from .models import Refrigerio, Participante

@require_POST
@ajax_login_required
@role_required(["ADMINISTRADOR", "OPERADOR_REFRIGERIO"])
def marcar_refrigerio(request):
    import json
    data = json.loads(request.body)
    participante = Participante.objects.get(documento=data["documento"])
    Refrigerio.objects.create(
        participante=participante,
        usuario_registro=request.user,
        tipo=data.get("tipo", "ALMUERZO")
    )
    return JsonResponse({"ok": True, "mensaje": "Refrigerio entregado"})
```

#### c) Protected URL Conf
```python
from django.urls import path
from .views import (DashboardAdminView, marcar_refrigerio,
                    ParticipanteListView, ParticipanteCreateView)

urlpatterns = [
    path("dashboard/", DashboardAdminView.as_view(), name="dashboard"),
    path("api/refrigerio/marcar/", marcar_refrigerio, name="refrigerio-marcar"),
    path("participantes/", ParticipanteListView.as_view(
        role_required=["ADMINISTRADOR","REGISTRO","OPERADOR_ASISTENCIA","OPERADOR_CERTIFICADO","CONSULTA"]
    ), name="participante-list"),
    path("participantes/nuevo/", ParticipanteCreateView.as_view(
        role_required=["ADMINISTRADOR","REGISTRO"],
        permission_required=("core.add_participante",)
    ), name="participante-create"),
]
```

### 6.4 Plantillas Jinja/Django — Bloques condicionales por rol

```html+django
{% load group_tags %}

{% if user|has_group:"ADMINISTRADOR" or user|has_group:"REGISTRO" %}
    <a href="{% url 'participante-create' %}" class="btn btn-primary">
        <i class="fa fa-plus"></i> Nuevo Participante
    </a>
{% endif %}

{% if user|has_group:"ADMINISTRADOR" %}
    <li class="nav-item"><a href="{% url 'configuracion' %}">Configuración</a></li>
{% endif %}
```

Con `templatetags/group_tags.py`:

```python
from django import template
register = template.Library()

@register.filter(name="has_group")
def has_group(user, group_name):
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()
```

---

## 7. Redirección Post-Login según Rol

### 7.1 Vista Login Personalizada

```python
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.utils import timezone
from seguridad.models import Profile

class CustomLoginView(LoginView):
    template_name = "seguridad/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        grupos = set(user.groups.values_list("name", flat=True))

        Profile.objects.filter(user=user).update(
            fecha_ultimo_acceso=timezone.now(),
            ip_ultimo_acceso=self._get_client_ip(self.request)
        )

        # PRIORIDAD de redirección según rol (sistema)
        if "OPERADOR_ASISTENCIA" in grupos:
            return "/asistencia/ingreso/"
        if "OPERADOR_REFRIGERIO" in grupos:
            return "/refrigerios/entrega/"
        if "OPERADOR_CERTIFICADO" in grupos:
            return "/certificados/generar/"
        if "REGISTRO" in grupos:
            return "/participantes/listado/"
        if "CONSULTA" in grupos:
            return "/reportes/"
        if "ADMINISTRADOR" in grupos:
            return "/dashboard/"

        # Usuario autenticado pero SIN grupo → logout + mensaje
        return "/sin-permiso/"

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
```

### 7.2 Configuración URL Login/Logout

```python
# urls.py proyecto
from django.contrib.auth import views as auth_views
from seguridad.views import CustomLoginView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/?logout=1"), name="logout"),
    path("sin-permiso/", TemplateView.as_view(template_name="seguridad/403.html"), name="sin-permiso"),
]

# settings.py
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"
```

---

## 8. Prueba Crítica de Permisos (Esperado: HTTP 403)

### 8.1 Casos de Prueba Automatizables (`tests/test_permisos.py`)

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse

class MatrizPermisosTest(TestCase):
    """
    Verifica MATRIZ de sección 3: respuesta 403 cuando rol NO tiene permiso.
    """

    @classmethod
    def setUpTestData(cls):
        g_admin = Group.objects.create(name="ADMINISTRADOR")
        g_oper_ref = Group.objects.create(name="OPERADOR_REFRIGERIO")
        g_sinrol = Group.objects.create(name="SIN_ROL_PRUEBA")

        cls.u_admin = User.objects.create_user("admin_prueba", password="S3naF3r14!")
        cls.u_admin.groups.add(g_admin)

        cls.u_refri = User.objects.create_user("refri_prueba", password="S3naF3r14!")
        cls.u_refri.groups.add(g_oper_ref)

        cls.u_sinrol = User.objects.create_user("sinrol_prueba", password="S3naF3r14!")
        cls.u_sinrol.groups.add(g_sinrol)

    # ------------------------------------------------------------------
    # TEST 1: OPERADOR_REFRIGERIO NO puede acceder a módulo CERTIFICADOS
    # ------------------------------------------------------------------
    def test_operador_refrigerio_NO_ve_certificados_espera_403(self):
        c = Client()
        c.login(username="refri_prueba", password="S3naF3r14!")
        r = c.get(reverse("certificado-list"))
        self.assertEqual(r.status_code, 403,
            "OPERADOR_REFRIGERIO debe recibir 403 al listar certificados")

    # ------------------------------------------------------------------
    # TEST 2: OPERADOR_ASISTENCIA / CUALQUIERA NO LOGUEADO → 302 o 401
    # ------------------------------------------------------------------
    def test_sin_login_redirige_a_login_302(self):
        c = Client()
        r = c.get(reverse("dashboard"))
        self.assertIn(r.status_code, (302, 401))

    # ------------------------------------------------------------------
    # TEST 3: OPERADOR_REFRIGERIO POST /api/certificado/generar → 403 JSON
    # ------------------------------------------------------------------
    def test_ajax_post_certificado_operador_refrigerio_403_json(self):
        c = Client()
        c.login(username="refri_prueba", password="S3naF3r14!")
        r = c.post(
            reverse("certificado-generar-ajax"),
            data={"documento": "123"},
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(r.status_code, 403,
            "POST AJAX a certificados por OPERADOR_REFRIGERIO debe ser 403")
        data = r.json()
        self.assertIn("403", str(data.get("codigo","")))
        self.assertEqual(data.get("ok"), False)

    # ------------------------------------------------------------------
    # TEST 4: ADMINISTRADOR SÍ puede entrar a Configuración (200)
    # ------------------------------------------------------------------
    def test_admin_SI_accede_configuracion_200(self):
        c = Client()
        c.login(username="admin_prueba", password="S3naF3r14!")
        r = c.get(reverse("configuracion"))
        self.assertEqual(r.status_code, 200)

    # ------------------------------------------------------------------
    # TEST 5: Rol SIN asignación intenta /configuracion → 403
    # ------------------------------------------------------------------
    def test_sinrol_intenta_configuracion_espera_403(self):
        c = Client()
        c.login(username="sinrol_prueba", password="S3naF3r14!")
        r = c.get(reverse("configuracion"))
        self.assertEqual(r.status_code, 403)

    # ------------------------------------------------------------------
    # TEST 6: CONSULTA (solo lectura) intenta POST delete → 403
    # ------------------------------------------------------------------
    def test_rol_consulta_no_puede_eliminar_participante_403(self):
        g_cons = Group.objects.create(name="CONSULTA")
        u_cons = User.objects.create_user("cons_prueba", password="S3naF3r14!")
        u_cons.groups.add(g_cons)
        c = Client()
        c.login(username="cons_prueba", password="S3naF3r14!")
        r = c.post(reverse("participante-delete", kwargs={"pk": 1}))
        self.assertEqual(r.status_code, 403)
```

### 8.2 Ejecutar Pruebas

```bash
# Activar entorno
.\venv\Scripts\activate

# Ejecutar solo tests de permiso
python manage.py test apps.seguridad.tests.test_permisos -v 2

# Reporte cobertura (si existe coverage)
coverage run manage.py test && coverage html
```

---

## 9. Configuración en settings.py y Custom Backend

### 9.1 Fragmento settings.py

```python
AUTH_USER_MODEL = "auth.User"               # o usuario personalizado
AUTH_PROFILE_MODULE = "seguridad.Profile"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/?bye=1"

# --- Seguridad headers ---
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False   # True en producción con HTTPS
CSRF_COOKIE_HTTPONLY = True

# --- Backend auth por defecto (Django Groups + Permissions) ---
AUTHENTICATION_BACKENDS = [
    "seguridad.backends.RoleEventoBackend",     # custom: añade contexto
    "django.contrib.auth.backends.ModelBackend", # default (requerido)
]

# --- Timeout sesiones operadores puerta ---
SESSION_COOKIE_AGE = 1800   # 30 minutos inactivos → logout auto

INSTALLED_APPS = [
    # ...
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # apps internas
    "apps.seguridad",
    "apps.core",          # eventos, instituciones, programas, proyectos
    "apps.ingreso",       # asistencia
    "apps.refrigerio",
    "apps.certificado",
    "apps.reportes",
]
```

### 9.2 Custom Backend (`seguridad/backends.py`)

```python
from django.contrib.auth.backends import ModelBackend

class RoleEventoBackend(ModelBackend):
    """
    Backend que NO reemplaza ModelBackend, solo anota en request.user atributos
    extras para plantillas: user.rol_sistema, user.rol_evento.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user and user.is_authenticated:
            self._anotar_roles(user)
        return user

    def get_user(self, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            self._anotar_roles(user)
            return user
        except User.DoesNotExist:
            return None

    @staticmethod
    def _anotar_roles(user):
        g = user.groups.first()
        user.rol_sistema = g.name if g else "SIN_ROL"
        try:
            user.rol_evento = user.profile.rol_evento
        except Exception:
            user.rol_evento = None
```

---

## FIN DE LA MATRIZ

> Documento riguroso de referencia técnica. Cualquier excepción de permisos debe ser
> aprobada por el administrador del proyecto y reflejada tanto aquí como en el
> comando `crear_roles_iniciales.py` y los tests de `test_permisos.py`.
