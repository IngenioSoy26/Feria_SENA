# FASE 0 — ANÁLISIS Y ARQUITECTURA DEL SISTEMA

> **Sistema de Gestión de Feria de Proyectos Productivos**
> **Programa de Articulación con la Educación Media — SENA Regional Guajira**
> Versión 1.0 | Octubre de 2026
> Color institucional SENA: `#39A900`

---

## 1. RESUMEN FUNCIONAL DEL SISTEMA

El sistema es una aplicación web **mobile-first, real y funcional** para gestionar la Feria de Proyectos Productivos del SENA Regional Guajira. Admite **múltiples eventos reutilizables** sin tocar el código. Permite:

1. **Administración de eventos**: crear ferias con nombre, fechas, lugar, municipio y regional.
2. **Catálogos maestros**: Instituciones Educativas, Programas Técnicos, Instructores.
3. **Modelo central de Personas** con token QR **UUID opaco** (sin datos personales).
4. **Proyectos productivos**: cada proyecto pertenece a una institución + programa + instructor responsable y tiene N aprendices.
5. **Invitados**: registro con entidad y cargo; pueden tener QR, escarapela y participar de los flujos.
6. **Escarapelas en PDF** (ReportLab): individuales, por proyecto, institución, programa, tipo de persona o evento completo.
7. **Ingreso/Asistencia** por QR desde celular con feedback VERDE/AMARILLO + búsqueda manual de contingencia.
8. **Control de Refrigerios** con servicios configurables por evento (mañana, almuerzo, tarde) y restricción única por persona + servicio (UniqueConstraint + transacciones para concurrencia).
9. **Control de Certificados** con entrega por QR y **URL pública de verificación** `/certificados/verificar/<token>/`.
10. **Dashboard administrativo** con Chart.js (16 KPIs + 12 gráficos + 7 filtros, actualización AJAX cada 30 s).
11. **Reportes Excel/PDF** por institución, programa, proyecto, instructor y general.
12. **Importación Excel** (openpyxl) validada: Instituciones, Programas, Instructores, Proyectos, Participantes.
13. **Auditoría (AuditLog)** de toda operación crítica con usuario, IP, fecha y JSON de cambios.
14. **RBAC estricto** con 6 perfiles de acceso y redirección por rol al iniciar sesión.
15. **PWA sencilla** con manifest + service worker para cachear CSS/JS/imágenes y permitir instalación.

---

## 2. REQUERIMIENTOS FUNCIONALES

| # | Módulo | Requerimiento |
|---|---|---|
| RF-01 | Eventos | CRUD Eventos (nombre, descripción, fecha_inicio, fecha_fin, lugar, municipio, regional, estado, activo). |
| RF-02 | Eventos | Activar/desactivar eventos; solo 1 evento por defecto seleccionable. |
| RF-03 | Usuarios | CustomUser con username, email, nombres, apellidos, rol sistema, activo, último acceso. |
| RF-04 | Usuarios | Autenticación Django + Groups + Permissions; 6 grupos de acceso. |
| RF-05 | Usuarios | Redirección post-login por perfil. |
| RF-06 | Personas | Modelo Persona central con tipo_identificacion, numero_identificacion, nombres, apellidos, correo, telefono, tipo_persona, qr_token. |
| RF-07 | Personas | Catálogo TipoIdentificacion extensible (TI, CC, PPT, ...). |
| RF-08 | Instituciones | CRUD + búsqueda + filtro + importación Excel. |
| RF-09 | Programas | CRUD ProgramaTecnico (código, nombre) + importación Excel. |
| RF-10 | Instructores | Perfil instructor asociado a Persona (no duplicado) + programas asociados M2M + importación Excel. |
| RF-11 | Proyectos | CRUD Proyecto (evento, código, nombre, descripción, institución, programa, instructor responsable, estado). |
| RF-12 | Proyectos | Asociar N aprendices a un proyecto desde su vista detalle. |
| RF-13 | Aprendices | Perfil Aprendiz 1:1 a Persona (FK a Proyecto, grado). |
| RF-14 | Invitados | Perfil Invitado 1:1 a Persona (entidad, cargo). |
| RF-15 | QR | Generar token UUID v4 único por Persona al crearla; QR NO contiene PII. |
| RF-16 | QR | Imagen QR generada con librería `qrcode` Python + logo SENA opcional. |
| RF-17 | Escarapelas | Generar PDF escarapela individual, por proyecto, por institución, por programa, por tipo persona, completo. |
| RF-18 | Escarapelas | Diseño A6 horizontal con logo SENA, nombre evento, nombre, rol, institución/programa/proyecto, QR. |
| RF-19 | Ingreso | Pantalla mobile-first Operador Asistencia: cámara + botón activar + contador + búsqueda manual. |
| RF-20 | Ingreso | UniqueConstraint(evento, persona) para no duplicar asistencia. |
| RF-21 | Ingreso | Estados: VERDE "INGRESO REGISTRADO" / AMARILLO "INGRESO REGISTRADO ANTERIORMENTE" / ROJO "QR INVÁLIDO". |
| RF-22 | Refrigerios | CRUD TipoServicio por evento (Refrigerio mañana, Almuerzo, Refrigerio tarde, ...) + marcar servicio activo. |
| RF-23 | Refrigerios | UniqueConstraint(evento, persona, tipo_servicio). |
| RF-24 | Refrigerios | Concurrencia protegida con `select_for_update()` + `transaction.atomic()` (solo 1 entrega aunque dos operadores escaneen en paralelo). |
| RF-25 | Certificados | UniqueConstraint(evento, persona) entrega; token_verificación UUID para URL pública. |
| RF-26 | Certificados | Página pública `/certificados/verificar/<token>/` muestra valido + nombre + evento + fecha SIN cédula ni correo ni teléfono. |
| RF-27 | Certificados | Preparar generación PDF certificado (fase posterior). |
| RF-28 | Dashboard | 16 KPIs + 12 gráficos Chart.js + 7 filtros (evento, institución, municipio, programa, proyecto, instructor, tipo persona). |
| RF-29 | Dashboard | Actualización AJAX cada 30 s + botón ACTUALIZAR manual. |
| RF-30 | Reportes | Excel de participantes, asistentes, ausentes, refrigerios, certificados + reporte general ejecutivo (Excel + PDF). |
| RF-31 | Importación Excel | Carga → validación → preview → confirmación. No guardar sin aprobación. |
| RF-32 | Importación Excel | Clasificar filas: VÁLIDOS / ADVERTENCIAS / ERRORES / DUPLICADOS. |
| RF-33 | Importación Excel | Descargar `errores_importacion.xlsx` con fila, campo, valor, error, recomendación. |
| RF-34 | Búsqueda Rápida | Buscar por identificación, nombre, proyecto, institución, instructor, programa (contingencia QR). |
| RF-35 | Auditoría | AuditLog con autor, acción, módulo, entidad, id_entidad, datos JSON, fecha, IP. |
| RF-36 | Auditoría | Señales Django post_save/post_delete + middleware para capturar IP + decorators manuales en vistas críticas. |
| RF-37 | Contingencia | Registro MANUAL con flag `medio = 'MANUAL'` y `'QR'` registrado en auditoría. |
| RF-38 | PWA | manifest.json, service-worker.js, iconos; cachear recursos estáticos (sin sincronización offline crítica). |
| RF-39 | Seed demo | Comando `python manage.py seed_demo` genera datos demo + 6 usuarios demo. |
| RF-40 | Tests | Pruebas automatizadas login, permisos 403, asistencia duplicada, concurrencia refrigerios, certificado único, importación, reportes, auditoría. |

---

## 3. REQUERIMIENTOS NO FUNCIONALES

| Categoría | Requerimiento |
|---|---|
| **Rendimiento** | Tiempo respuesta < 1.5 s en operaciones típicas (escaneo QR → respuesta). Dashboard carga < 3 s con 500 participantes. |
| **Disponibilidad** | 99.5% durante el evento; sin punto único de fallo en capa de aplicación. SQLite local para MVP. |
| **Seguridad** | CSRF en todo formulario/AJAX. CSP Level 3. XSS prevenido. Contraseñas Argon2. Cookies Secure, HttpOnly, SameSite=Lax. URLs sin token en historial. |
| **Minimización PII** | QR NO contiene PII. Pantallas operador solo muestran nombre, rol, institución/proyecto (no cédula completa por defecto). |
| **Movilidad** | Mobile-first: resolución base 360×640. Botones ≥ 48×48 px. Botones principales en la parte inferior. Lector QR usa cámara trasera por defecto. |
| **Compatibilidad** | Chrome 110+, Safari 16+, Edge 110+, Firefox 110+. iOS 15+, Android 10+. |
| **Accesibilidad** | WCAG 2.1 AA: contraste ≥ 4.5:1 texto normal, ≥ 3:1 texto grande. Tab order visible. ARIA labels en lector QR. |
| **Escalabilidad** | 300-1000 participantes por evento. 5 operadores concurrentes escaneando sin duplicados. |
| **Mantenibilidad** | Arquitectura modular 13 apps Django. Tests automatizados ≥ 60% cobertura. Documentación técnica. |
| **Internacionalización** | Español colombiano `es-CO`. Time zone `America/Bogota`. Formato moneda y fechas CO. |
| **Despliegue** | Compatible con PythonAnywhere (Python 3.10, SQLite o MySQL). Sin dependencias nativas pesadas (ReportLab sobre Cairo). |
| **Offline** | PWA cachea CSS, JS, logo SENA, imágenes. NO sincroniza operaciones críticas offline (asistencia/refrigerios siempre requieren servidor). |

---

## 4. ARQUITECTURA DJANGO PROPUESTA

**Patrón**: MVT (Model-View-Template) de Django + capa de Servicios para lógica de negocio compleja.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PRESENTACIÓN (Templates)                      │
│  base.html · Bootstrap 5 · Work Sans · #39A900 · html5-qrcode · Chart.js│
│  Pantallas operador mobile-first · Dashboard · Formularios CRUD         │
└──────────────────────────────────────┬──────────────────────────────────┘
                                       │ HTTP + Fetch/AJAX
┌──────────────────────────────────────▼──────────────────────────────────┐
│                      CONTROLADORES (Vistas CBV + FBV)                   │
│  LoginRequired · PermissionRequired · RoleRequiredMixin · AJAX JSON     │
│  Redirección post-login por rol · Validación backend 100%               │
└──────────────────────────────────────┬──────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────┐
│               CAPA DE SERVICIOS (services.py por app)                   │
│  AsistenciaService · RefrigerioService · CertificadoService             │
│  ImportacionExcelService · EscarapelaPDFService · AuditoriaService      │
└──────────────────────────────────────┬──────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────┐
│                           MODELS + ORM DJANGO                           │
│  14 modelos · UniqueConstraints · UUID tokens · transacciones atómicas  │
│  select_for_update() en refrigerios · Señales para auditoría            │
└──────────────────────────────────────┬──────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────┐
│                 BASE DE DATOS · SQLite (dev/produccion PA)              │
│         + media/ (QR PNG, PDFs generados)  +  static/ (CSS/JS/img)      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. DIAGRAMA DE ARQUITECTURA COMPLETO (ASCII)

```
                        USUARIO FINAL
                      (Celular / Tablet)
                     Chrome/Safari HTTPS
                              │
                              ▼
                    ┌──────────────────┐
                    │   PythonAnywhere  │
                    │  (Load Balancer)  │
                    └────────┬─────────┘
                             │ HTTPS/WSS
                             ▼
    ┌─────────────────────────────────────────────────────────┐
    │                WSGI (Django App) · whitenoise            │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │  MIDDLEWARE STACK:                                │  │
    │  │  SecurityMiddleware · SessionMiddleware           │  │
    │  │  CsrfViewMiddleware · AuthMiddleware              │  │
    │  │  MessageMiddleware · CustomAuditMiddleware        │  │
    │  │  CSPMiddleware (django-csp) · GZipMiddleware      │  │
    │  └───────────────────┬───────────────────────────────┘  │
    │                      ▼                                  │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │          URL Routing (config/urls.py)             │  │
    │  │  cada app con su urls.py y namespace propio       │  │
    │  └───────────────────┬───────────────────────────────┘  │
    │                      ▼                                  │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │  Vistas · Mixins RBAC · Permisos por endpoint    │  │
    │  │  Respuestas: HTML Templates + JSON AJAX           │  │
    │  └───────────────────┬───────────────────────────────┘  │
    │                      ▼                                  │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │  ORM Django · Transacciones · Constraints         │  │
    │  └───────────────────┬───────────────────────────────┘  │
    └──────────────────────┼──────────────────────────────────┘
                           │
              ┌────────────┼──────────────┐
              ▼            ▼              ▼
        ┌─────────┐  ┌─────────┐   ┌─────────────┐
        │ SQLite  │  │ Media/  │   │ Static/     │
        │  .db    │  │ QR  PNG │   │ whitenoise  │
        └─────────┘  │ PDFs    │   │ cache HTTP  │
                     └─────────┘   └─────────────┘
                              ┌──────────────┐
                              │ Librerias    │
                              │ ReportLab    │
                              │ openpyxl     │
                              │ qrcode       │
                              │ Pillow       │
                              └──────────────┘
```

---

## 6. ESTRUCTURA DE APLICACIONES DJANGO

```
c:\Feria_2026\
├── config/                     ← Paquete de proyecto (startproject)
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py             ← configuracion comun
│       ├── development.py      ← DEBUG=True, SQLite local
│       └── production.py       ← DEBUG=False, whitenoise, ALLOWED_HOSTS
├── apps/
│   ├── __init__.py
│   ├── core/                   ← mixins, templatetags, utils, helpers, PWA
│   ├── usuarios/               ← CustomUser, Group seed, Profile, auth views
│   ├── eventos/                ← Evento, TipoIdentificacion, TipoServicio
│   ├── instituciones/          ← InstitucionEducativa
│   ├── programas/              ← ProgramaTecnico
│   ├── personas/               ← Persona (CENTRAL) + generador QR
│   ├── proyectos/              ← Proyecto + Aprendiz (rel proyecto)
│   ├── instructores/           ← Instructor (1:1 Persona, M2M programas)
│   ├── invitados/              ← Invitado (1:1 Persona)
│   ├── escarapelas/            ← ReportLab PDF escarapelas, lotes
│   ├── asistencia/             ← AsistenciaEvento + vista lector QR
│   ├── refrigerios/            ← EntregaServicio + vista lector QR
│   ├── certificados/           ← Certificado + URL publica verificacion
│   ├── dashboard/              ← Chart.js dashboard, AJAX endpoints
│   ├── reportes/               ← Excel openpyxl + PDF ReportLab ejecutivo
│   └── auditoria/              ← AuditLog + signals + panel admin
├── templates/                  ← templates base (Django Template Language)
│   ├── base.html
│   ├── base_operador.html      ← mobile-first minimal (sin sidebar)
│   ├── registration/login.html
│   └── (un subfolder por app)
├── static/
│   ├── css/sena.css            ← variables #39A900, Work Sans
│   ├── js/html5-qrcode.min.js
│   ├── js/chart.min.js
│   ├── js/app.js
│   ├── img/logo-sena-verde.png
│   └── manifest.json
├── media/
│   └── .gitkeep
├── docs/                       ← documentación
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

**Justificación número de apps**: 16 apps. Cada app tiene una **única responsabilidad funcional real**. No se crean apps "vacías": todo lo que está en el nombre tiene modelos/vistas/tareas únicas.

---

## 7. DIAGRAMA ENTIDAD-RELACIÓN (ER ASCII)

```
 CustomUser (1) ──┐
                  │ crea / modifica
                  ▼
   ┌────────── Evento ─────────┐
   │ (PK) id                   │
   │  nombre, fechas, lugar    │
   │  municipio, regional      │
   │  estado, activo           │
   └──┬─────────┬──────────┬───┘
      │         │          │ FK
      ▼         ▼          ▼
   Institucion Programa  TipoServicio
   Educativa   Tecnico   (nombre, activo)
      │         │
      │ FK      │ FK      Instructor ─────── Persona (1:1)
      ▼         ▼          (FK persona)       (CENTRAL)
   ┌──────── Proyecto ──────┐          tipo_id,numero_id,nombres,
   │ codigo,nombre,desc     │          apellidos,correo,telefono,
   │ estado                 │          tipo_persona,qr_token UUID,activo
   └────────┬───────────────┘               ▲      ▲         ▲
            │ FK instructor responsable     │      │         │
            │                               │      │         │
            │                               │ 1:1  1:1      1:1
            │                               │      │         │
            ├──────── Aprendiz ─────────────┘  Invitado    (Organizador=rol, sin tabla)
            │ (proyecto FK, grado)           (entidad, cargo)
            │
            │ (Aprendiz → persona, Instructor → persona, Invitado → persona)
            │ = TODOS comparten ID Persona y su único QR_token
            │
            ▼
     AsistenciaEvento [UQ(evento,persona)]
       fecha_hora, operador FK, medio(QR/MANUAL)

     EntregaServicio [UQ(evento,persona,tipo_servicio)]
       fecha_hora, operador FK, medio

     Certificado [UQ(evento,persona)]
       codigo_unico, token_verificacion UUID,
       fecha_hora_entrega, operador FK, medio

     AuditLog
       usuario FK, accion, modulo, entidad,
       id_entidad, datos JSON, fecha_hora, ip
```

---

## 8. PROPUESTA COMPLETA DE MODELOS DJANGO

**Abreviaturas**: `PK=AutoField` / `FK=ForeignKey` / `UQ=UniqueConstraint` / `M2M=ManyToMany` / `CK=CheckConstraint` / `UUID=uuid4`

### 8.1. CustomUser (app: `usuarios`)
```python
class Usuario(AbstractUser):
    ROLES_SISTEMA = (
        ('ADMINISTRADOR', 'Administrador'),
        ('REGISTRO',      'Registro'),
        ('OPERADOR_ASISTENCIA',   'Operador de Asistencia'),
        ('OPERADOR_REFRIGERIO',   'Operador de Refrigerio'),
        ('OPERADOR_CERTIFICADO',  'Operador de Certificado'),
        ('CONSULTA',      'Consulta'),
    )
    email       = models.EmailField(unique=True)
    nombres     = models.CharField(max_length=120)
    apellidos   = models.CharField(max_length=120)
    rol_sistema = models.CharField(max_length=30, choices=ROLES_SISTEMA, db_index=True)
    activo      = models.BooleanField(default=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    REQUIRED_FIELDS = ['email', 'nombres', 'apellidos', 'rol_sistema']
```

### 8.2. Evento + TipoIdentificacion + TipoServicio (app: `eventos`)
```python
class TipoIdentificacion(models.Model):
    codigo = models.CharField(max_length=10, unique=True)   # 'CC','TI','PPT',...
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

class Evento(models.Model):
    ESTADOS = (('BORRADOR','Borrador'),('ACTIVO','Activo'),('CERRADO','Cerrado'))
    nombre          = models.CharField(max_length=200)
    descripcion     = models.TextField(blank=True)
    fecha_inicio    = models.DateField()
    fecha_fin       = models.DateField()
    lugar           = models.CharField(max_length=200)
    municipio       = models.CharField(max_length=100)
    regional        = models.CharField(max_length=100, default='Guajira')
    estado          = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')
    activo          = models.BooleanField(default=True, db_index=True)
    creado_por      = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-fecha_inicio']

class TipoServicio(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='tipos_servicio')
    nombre = models.CharField(max_length=60)  # 'Refrigerio mañana','Almuerzo','Refrigerio tarde'
    orden  = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=False, db_index=True,
        help_text='Solo 1 servicio activo para entrega a la vez por evento')
    class Meta:
        constraints = [
            UniqueConstraint(fields=['evento','nombre'], name='uq_tiposervicio_evento_nombre'),
        ]
```

### 8.3. Persona (app: `personas`) — MODELO CENTRAL
```python
class Persona(models.Model):
    TIPOS = (
        ('APRENDIZ',     'Aprendiz'),
        ('INSTRUCTOR',   'Instructor'),
        ('INVITADO',     'Invitado'),
        ('ORGANIZADOR',  'Organizador'),
    )
    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT)
    numero_identificacion = models.CharField(max_length=30, db_index=True)
    nombres   = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    correo    = models.EmailField(null=True, blank=True)
    telefono  = models.CharField(max_length=30, null=True, blank=True)
    tipo_persona = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    qr_token  = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    activo    = models.BooleanField(default=True)
    creado_por = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            UniqueConstraint(fields=['tipo_identificacion','numero_identificacion'],
                             name='uq_persona_tipo_numero_id'),
        ]
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()
```

### 8.4. InstitucionEducativa (app: `instituciones`)
```python
class InstitucionEducativa(models.Model):
    nombre     = models.CharField(max_length=250, unique=True)
    municipio  = models.CharField(max_length=100)
    secretaria_educacion = models.CharField(max_length=150, blank=True)
    codigo     = models.CharField(max_length=30, unique=True)
    activo     = models.BooleanField(default=True)
```

### 8.5. ProgramaTecnico (app: `programas`)
```python
class ProgramaTecnico(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)
```

### 8.6. Instructor (app: `instructores`)
```python
class Instructor(models.Model):
    persona  = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name='perfil_instructor')
    programas = models.ManyToManyField(ProgramaTecnico, blank=True, related_name='instructores')
    activo   = models.BooleanField(default=True)
```

### 8.7. Invitado (app: `invitados`)
```python
class Invitado(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name='perfil_invitado')
    entidad = models.CharField(max_length=200)
    cargo   = models.CharField(max_length=150)
```

### 8.8. Proyecto + Aprendiz (app: `proyectos`)
```python
class Proyecto(models.Model):
    ESTADOS = (('INSCRITO','Inscrito'),('APROBADO','Aprobado'),('RETIRADO','Retirado'))
    evento       = models.ForeignKey(Evento, on_delete=models.PROTECT, related_name='proyectos')
    codigo       = models.CharField(max_length=40, db_index=True)
    nombre       = models.CharField(max_length=250)
    descripcion  = models.TextField(blank=True)
    institucion  = models.ForeignKey(InstitucionEducativa, on_delete=models.PROTECT, related_name='proyectos')
    programa     = models.ForeignKey(ProgramaTecnico, on_delete=models.PROTECT, related_name='proyectos')
    instructor_responsable = models.ForeignKey(Instructor, null=True, on_delete=models.SET_NULL, related_name='proyectos_dirigidos')
    estado       = models.CharField(max_length=20, choices=ESTADOS, default='INSCRITO')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            UniqueConstraint(fields=['evento','codigo'], name='uq_proyecto_evento_codigo'),
        ]

class Aprendiz(models.Model):
    persona   = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name='perfil_aprendiz')
    proyecto  = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='aprendices')
    grado     = models.CharField(max_length=10, default='11')
    class Meta:
        ordering = ['persona__apellidos','persona__nombres']
```

### 8.9. AsistenciaEvento (app: `asistencia`)
```python
class AsistenciaEvento(models.Model):
    MEDIOS = (('QR','QR'),('MANUAL','Búsqueda Manual'))
    evento    = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='asistencias')
    persona   = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='asistencias')
    fecha_hora = models.DateTimeField(auto_now_add=True)
    operador  = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    medio     = models.CharField(max_length=10, choices=MEDIOS, default='QR')
    class Meta:
        constraints = [
            UniqueConstraint(fields=['evento','persona'], name='uq_asistencia_evento_persona'),
        ]
```

### 8.10. EntregaServicio (app: `refrigerios`)
```python
class EntregaServicio(models.Model):
    MEDIOS = (('QR','QR'),('MANUAL','Búsqueda Manual'))
    evento        = models.ForeignKey(Evento, on_delete=models.CASCADE)
    persona       = models.ForeignKey(Persona, on_delete=models.CASCADE)
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.PROTECT)
    fecha_hora    = models.DateTimeField(auto_now_add=True)
    operador      = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    medio         = models.CharField(max_length=10, choices=MEDIOS, default='QR')
    class Meta:
        constraints = [
            UniqueConstraint(fields=['evento','persona','tipo_servicio'],
                             name='uq_entrega_evento_persona_servicio'),
        ]
```

### 8.11. Certificado (app: `certificados`)
```python
class Certificado(models.Model):
    MEDIOS = (('QR','QR'),('MANUAL','Búsqueda Manual'))
    evento      = models.ForeignKey(Evento, on_delete=models.CASCADE)
    persona     = models.ForeignKey(Persona, on_delete=models.CASCADE)
    codigo_unico = models.CharField(max_length=40, unique=True, editable=False)
    token_verificacion = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    fecha_hora_entrega = models.DateTimeField(auto_now_add=True)
    operador    = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    medio       = models.CharField(max_length=10, choices=MEDIOS, default='QR')
    def save(self, *a, **k):
        if not self.codigo_unico:
            self.codigo_unico = f"SENA-{self.evento_id}-{self.persona_id}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*a, **k)
    class Meta:
        constraints = [
            UniqueConstraint(fields=['evento','persona'], name='uq_certificado_evento_persona'),
        ]
```

### 8.12. AuditLog (app: `auditoria`)
```python
class AuditLog(models.Model):
    ACCIONES = (('CREATE','Crear'),('UPDATE','Modificar'),('DELETE','Eliminar'),
                ('LOGIN','Login'),('LOGOUT','Logout'),('IMPORT','Importación'),
                ('ASISTENCIA','Asistencia'),('REFRIGERIO','Refrigerio'),
                ('CERTIFICADO','Certificado'))
    usuario     = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL)
    accion      = models.CharField(max_length=20, choices=ACCIONES, db_index=True)
    modulo      = models.CharField(max_length=50, db_index=True)
    entidad     = models.CharField(max_length=100, null=True)
    id_entidad  = models.PositiveIntegerField(null=True)
    datos       = models.JSONField(null=True, blank=True)
    fecha_hora  = models.DateTimeField(auto_now_add=True, db_index=True)
    ip          = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.CharField(max_length=255, blank=True)
```

---

## 9. RESUMEN DE RELACIONES Y CARDINALIDADES

| Entidad A | Relación | Entidad B | Cardinalidad |
|---|---|---|---|
| Usuario | crea | Evento | 1:N |
| Evento | contiene | Proyecto | 1:N |
| Evento | define | TipoServicio | 1:N |
| Evento | registra | AsistenciaEvento | 1:N |
| Evento | registra | EntregaServicio | 1:N |
| Evento | entrega | Certificado | 1:N |
| InstitucionEducativa | tiene | Proyecto | 1:N |
| ProgramaTecnico | tiene | Proyecto | 1:N |
| Instructor | dirige | Proyecto | 1:N (dirige) |
| Instructor | M2M | ProgramaTecnico | N:M |
| Proyecto | agrupa | Aprendiz | 1:N |
| Persona | es | Aprendiz | 1:1 (opcional) |
| Persona | es | Instructor | 1:1 (opcional) |
| Persona | es | Invitado | 1:1 (opcional) |
| Persona | asiste | AsistenciaEvento | 1:N (por eventos distintos) |
| Persona | recibe | EntregaServicio | 1:N |
| Persona | recibe | Certificado | 1:N (por eventos distintos) |
| TipoServicio | es | EntregaServicio | 1:N |

---

## 10. PROPUESTA DEL MODELO PERSONA (CENTRAL) — JUSTIFICACIÓN

Se adopta **un solo modelo `Persona` central** con 3 tablas hijas 1:1 opcionales (`Aprendiz`, `Instructor`, `Invitado`).

**5 razones sobre alternativa de 3 tablas separadas**:

1. **Identidad única por individuo**: un instructor puede ser también aprendiz en otro contexto o un invitado que fue aprendiz años anteriores — tener una sola identidad evita duplicados de cédula/correo/teléfono.
2. **QR único por persona**: el token UUID es una sola entidad. Si Persona fuera 3 tablas, el QR apuntaría a 3 modelos distintos → lógica más compleja, 3 búsquedas, más punto de fallo.
3. **Transacciones limpias**: AsistenciaEvento / EntregaServicio / Certificado tienen 1 FK a Persona, en lugar de 3 FK nulas + constraint.
4. **Minimización PII**: un solo lugar donde se almacenan datos personales → fácil auditar y eliminar (derecho al olvido).
5. **Reportes más simples**: conteo total de participantes es COUNT(Persona) sin JOINs de unión.

Riesgo mitigado: si alguna tabla hija requiere campos especiales, van en su tabla hija sin alterar el núcleo.

---

## 11. CÓMO DISTINGUIR APRENDIZ, INSTRUCTOR E INVITADO SIN DUPLICAR

**Dos capas simultáneas**:

- **Hint de consulta rápida**: campo `Persona.tipo_persona` (choices APRENDIZ/INSTRUCTOR/INVITADO/ORGANIZADOR). Útil para filtros rápidos y listados generales.
- **Verdad de fuente única**: existencia de fila en tabla hija 1:1:
  - Si `persona.perfil_aprendiz` existe → Aprendiz.
  - Si `persona.perfil_instructor` existe → Instructor.
  - Si `persona.perfil_invitado` existe → Invitado.

**Roles múltiples**: una misma Persona puede ser Instructor + Invitado? Por defecto se permite (orgánicamente el diseño lo permite, sin bloqueos). Si el negocio requiere exclusividad, un `clean()` en los perfiles lo valida.

**No hay duplicación**: nombres, identificación, correo, teléfono, QR viven en `Persona`. Las tablas hijas solo tienen campos exclusivos de ese perfil (ej: Aprendiz.grado, Invitado.entidad/cargo, Instructor M2M programas).

---

## 12. MODELO PROYECTO Y PARTICIPANTES

```
 Proyecto
 ├── evento FK
 ├── código único por evento
 ├── nombre, descripción, estado (INSCRITO/APROBADO/RETIRADO)
 ├── InstitucionEducativa FK  ← "I.E. San Juan Bautista"
 ├── ProgramaTecnico FK       ← "ASIS ADMINISTRATIVA"
 ├── Instructor FK            ← responsable (SOREN ROMERO, etc.)
 ├── fecha_creacion
 └── related_name='aprendices' ← N Aprendices (cada uno con: Persona 1:1 + proyecto FK + grado)
```

- **Un Proyecto → N Aprendices**: 2-40 por proyecto.
- **Una Institución → N Proyectos** (distintos programas o distintos grupos).
- **Un Programa → N Proyectos** (en varias I.E.).
- **Un Instructor → N Proyectos** como responsable.

**Vista detalle Proyecto**: muestra datos generales + instructor + lista aprendices + botones "Agregar aprendiz", "Editar", "Escarapelas del proyecto", "Asistencia del proyecto".

---

## 13. ARQUITECTURA DE USUARIOS

```
 AbstractUser (Django)
       │ extends
       ▼
 Usuario (CustomUser app: usuarios)
 ┌────────────────────────────────────────────────────────────┐
 │ username · password (Argon2) · email (único)              │
 │ nombres · apellidos · rol_sistema (6 valores)             │
 │ activo · ultimo_acceso · is_staff · is_superuser          │
 │ last_login (Django) · date_joined (Django)                │
 └───────────────────────┬────────────────────────────────────┘
                         │ asocia con Group de Django mediante
                         │  django.contrib.auth.models.Group
                         │
         ┌───────────────┼──────────────────┐
         ▼               ▼                  ▼
   Grupo "Admin"    Grupo "Registro"    Grupo "OperadorAsistencia"  ...
   (permisos C/R/U/D  (permisos C/R/U en   (solo permiso
    en TODO)           catálogos)           'asistencia.registrar')
```

- **Seeding inicial**: comando `usuarios/management/commands/crear_roles_iniciales.py` que crea 6 Group + asigna permisos por `codename`.
- **Login**: vista `LoginView` custom que captura grupo y redirige según `rol_sistema`.
- **User backend por defecto** (`ModelBackend`) es suficiente; Groups/Permissions nativos.

---

## 14. MATRIZ COMPLETA DE ROLES Y PERMISOS

Simbología: `C`=Crear · `R`=Leer · `U`=Actualizar · `D`=Eliminar · `-`=Sin acceso. **Protegido en backend con PermissionRequiredMixin + custom 403** (no solo ocultar botones).

| MÓDULO | ADMINISTRADOR | REGISTRO | OPERADOR_ASISTENCIA | OPERADOR_REFRIGERIO | OPERADOR_CERTIFICADO | CONSULTA |
|---|---|---|---|---|---|---|
| **Dashboard** | CR | R | - | - | - | R |
| **Eventos** | CRUD | R | - | - | - | - |
| **Usuarios y permisos** | CRUD | - | - | - | - | - |
| **Instituciones** | CRUD | CRU | - | - | - | R |
| **Programas técnicos** | CRUD | CRU | - | - | - | R |
| **Instructores** | CRUD | CRU | - | - | - | R |
| **Proyectos** | CRUD | CRU | - | - | - | R |
| **Personas / Participantes** | CRUD | CRU | R | R | R | R |
| **Aprendices (perfil)** | CRUD | CRU | R | - | - | R |
| **Invitados** | CRUD | CRU | R | R | R | R |
| **Escarapelas (PDF)** | CR | R | R | - | - | R |
| **Ingreso / Asistencia** | CRU | R | **CR** | - | - | R |
| **Refrigerios (entrega)** | CRU | - | - | **CR** | - | R |
| **Certificados (entrega)** | CRU | - | - | - | **CR** | R |
| **Verificación pública certificados** | R | R | R | R | R | R | (pública, sin login) |
| **Reportes Excel/PDF** | CR | R | - | - | - | R |
| **Auditoría** | R | - | - | - | - | - |
| **Configuración** | U | - | - | - | - | - |
| **Importación Excel** | CRU | CRU | - | - | - | - |
| **Búsqueda rápida contingencia** | CRU | R | **R** | **R** | **R** | R |

Nota: Los operadores **sí** pueden usar Búsqueda Rápida como contingencia del QR. El `medio='MANUAL'` queda registrado en `AuditLog`.

---

## 15. FLUJO DE AUTENTICACIÓN

```
  USUARIO                         SERVIDOR DJANGO
     │ POST /accounts/login/            │
     │ username, password, CSRF         │
     │──────────────────────────────────▶
     │                                  │ ▼ authenticate(username,pwd)
     │                                  │   ▼ LoginView.form_valid()
     │                                  │   ▼ AuditLog LOGIN + ip
     │                                  │   ▼ actualizar ultimo_acceso
     │                                  │   ▼ get_redirect_url() by rol:
     │                                  │      ADMIN/REGISTRO/CONSULTA → /dashboard/
     │                                  │      ASISTENCIA  → /asistencia/ingreso/
     │                                  │      REFRIGERIO  → /refrigerios/entrega/
     │                                  │      CERTIFICADO → /certificados/entrega/
     │◀─────────────────────────────────│
     │    302 Redirect al módulo        │
     │                                  │
     │ GET /asistencia/ingreso/         │
     │ (Cookie sessionid HttpOnly)      │
     │──────────────────────────────────▶
     │                                  │ ▼ LoginRequiredMixin
     │                                  │ ▼ RoleRequiredMixin(ASISTENCIA|ADMIN)
     │◀─────────────────────────────────│
     │  200 HTML mobile-first lector    │
```

---

## 16. FLUJO DE QR

**IMPORTANTE**: El QR **NO contiene** nombre, cédula, teléfono, correo, proyecto. Solo un UUID opaco.

```
  CELULAR OPERADOR                 SERVIDOR DJANGO                  DB
       │ html5-qrcode scan              │                              │
       │ qr_token = "a1b2c3-...-uuid"  │                              │
       │                                │                              │
       │ POST /asistencia/api/validar/ │                              │
       │ body: { token, csrf }         │                              │
       │───────────────────────────────▶                              │
       │                               │                              │
       │                               │▼ Persona.objects.get         │
       │                               │    (qr_token=token).select_  │
       │                               │    related('perfil_aprendiz',│
       │                               │     'perfil_instructor',...) │
       │                               │                              │
       │                               │▼ NO EXISTE → return JSON    │
       │◀──────────────────────────────│ { "status":"ROJO", ... }    │
       │                               │                              │
       │                               │▼ EXISTE → devuelve datos    │
       │◀──────────────────────────────│ { status:"OK",               │
       │                               │   nombre, rol, institucion,  │
       │                               │   proyecto }                 │
       │                               │                              │
       │ (operador confirma / auto)    │                              │
       │ POST /asistencia/api/registrar/                             │
       │ { token, evento_id, medio }  │                              │
       │───────────────────────────────▶                              │
       │                               │▼ transaction.atomic         │
       │                               │  get_or_create(Asistencia)   │
       │                               │  AuditLog accion=ASISTENCIA  │
       │◀──────────────────────────────│                              │
       │ { status:"VERDE" o "AMARILLO"│                              │
       │   fecha_hora, operador }     │                              │
       │                               │                              │
       └── (1.5 s feedback → auto regresa al lector) ────────────────┘
```

---

## 17. FLUJO DE ESCARAPELAS

```
  Admin / Registro selecciona origen:
    • Individual  (persona_id)
    • Por Proyecto (proyecto_id)
    • Por Institución
    • Por Programa
    • Por Tipo Persona (APRENDIZ / INSTRUCTOR / INVITADO)
    • Todo el Evento
              │
              ▼
  EscarapelaPDFService.generar(qs_personas, plantilla)
    ├── Consulta personas (select_related perfiles + institucion + programa + proyecto)
    ├── Para cada persona:
    │     ├── Generar QR PNG si no existe en media/qr/<token>.png
    │     ├── Componer canvas ReportLab (A6 horizontal 148×105 mm)
    │     │     ├── Banda superior verde #39A900
    │     │     ├── Logo SENA PNG
    │     │     ├── Nombre evento (Arial/WorkSans Bold 10)
    │     │     ├── Nombre completo (Bold 18)
    │     │     ├── Rol (badge con color por rol)
    │     │     │       Aprendiz    = #39A900
    │     │     │       Instructor  = #0067B1 (azul SENA complementario)
    │     │     │       Invitado    = #F57C00 (naranja)
    │     │     ├── Institución / Programa / Proyecto (si aplica)
    │     │     └── QR (3×3 cm mínimo)
    │     └── Añadir página
    └── HttpResponse(content_type='application/pdf')
              │
              ▼
       Descarga inmediata `escarapelas_{lote}_{timestamp}.pdf`
```

---

## 18. FLUJO DE INGRESO (ASISTENCIA)

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │ VISTA: /asistencia/ingreso/  (solo ADMINISTRADOR y OPERADOR_ASISTENCIA)│
 │  - Barra superior: logo SENA + nombre evento + nombre operador       │
 │  - Contador en vivo: "47 / 230 ingresos registrados"                 │
 │  - Botón GRANDE #39A900: [ACTIVAR CÁMARA] (48×48 px +)              │
 │  - Botón secundario:  [BUSCAR PERSONA] (contingencia QR falla)      │
 │  - Zona visor cámara (16:9, fija)                                   │
 │  - Panel de resultado (oculto hasta escaneo)                        │
 └────────────────────────────┬─────────────────────────────────────────┘
                              │ Escaneo QR (html5-qrcode, camara trasera)
                              ▼
                   AJAX /asistencia/api/registrar/
                              │
                              ▼
                ┌───────────────────────────────┐
                │ 1. Lookup Persona by qr_token │
                │    NO EXISTE → ROJO           │
                └───────────────┬───────────────┘
                                ▼
                ┌───────────────────────────────┐
                │ 2. Validar que evento activo  │
                │    corresponde (UQ)           │
                └───────────────┬───────────────┘
                                ▼
                ┌────────────────────────────────────────────┐
                │ 3. get_or_create(AsistenciaEvento)          │
                │    + UniqueConstraint a nivel BD            │
                └───────────────┬────────────────────────────┘
                                ▼
                     ┌──────────┴────────────┐
                     ▼                       ▼
             created=True              created=False
             (PRIMER INGRESO)          (YA REGISTRÓ)
             VERDE #2E7D32             AMARILLO #F9A825
             "INGRESO REGISTRADO"      "INGRESO REGISTRADO ANTERIORMENTE"
             Muestra nombre, rol,      Muestra fecha_hora original
             institución, proyecto     y operador original
                                │
                                ▼
          Mostrar panel de resultado 1.5 s → auto ocultar → reiniciar lector
```

---

## 19. FLUJO DE REFRIGERIOS

```
 VISTA: /refrigerios/entrega/  (solo ADMINISTRADOR y OPERADOR_REFRIGERIO)
   └─ Muestra además: SERVICIO ACTIVO = "Almuerzo" (obligatorio al menos 1)

 AJAX POST /refrigerios/api/entregar/
     { token, medio }
     │
     ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ RefrigerioService.entregar(evento, token, operador, medio):       │
 │                                                                   │
 │  1. with transaction.atomic():                                    │
 │  2.    TipoServicio.objects.select_for_update()                   │
 │            .get(evento=evento, activo=True)  ← servicio activo    │
 │  3.    Persona.objects.get(qr_token=token)                        │
 │  4.    ¿Ya existe EntregaServicio(evento,p,tipo_servicio)?        │
 │          SÍ → return AMARILLO (fecha original + operador)         │
 │  5.    (otro hilo concurrente puede habernos ganado)              │
 │          → catch IntegrityError (UniqueConstraint)                │
 │          → re-lanzar consulta y devolver AMARILLO                 │
 │  6.    NO → crear EntregaServicio + AuditLog REFRIGERIO           │
 │  7.    return VERDE + persona.nombre + rol + fecha                │
 └──────────────────────────────────────────────────────────────────┘

 PRUEBA CRÍTICA: 2 threads simultáneos POSTean mismo refrigerio misma persona
   → RESULTADO ESPERADO: 1 fila en EntregaServicio, 1 respuesta VERDE, 1 AMARILLO
   (NO debe haber 2 filas)
```

---

## 20. FLUJO DE CERTIFICADOS

```
 VISTA: /certificados/entrega/  (solo ADMINISTRADOR y OPERADOR_CERTIFICADO)

 AJAX POST /certificados/api/entregar/
   ├── get_or_create con UQ(evento,persona)
   ├── created=True → VERDE "CERTIFICADO ENTREGADO"
   └── created=False → AMARILLO "CERTIFICADO ENTREGADO ANTERIORMENTE"

 GENERAR PDF (preparado, diseño final requiere aprobación):
   ReportLab A4 · Banda superior #39A900 · Logo SENA
   Título "CERTIFICADO DE PARTICIPACIÓN"
   Texto: "El SENA Regional Guajira certifica que <NOMBRE> participó como <ROL>
           en el Proyecto <PROYECTO> durante el evento <EVENTO> realizado en
           <FECHA> en <LUGAR>."
   Código único + QR de verificación que apunta a la URL pública.

 URL PÚBLICA (SIN LOGIN):
   GET /certificados/verificar/<token_verificacion>/
   Responde:
     ✅ CERTIFICADO VÁLIDO
        Nombre: MARIA GOMEZ PEREZ
        Evento: Feria Proyectos Productivos 2026
        Fecha de entrega: 2026-11-20 10:30
        Código: SENA-1-234-ABC12345
   (NUNCA mostrar cédula, teléfono, correo, QR del asistido)
```

---

## 21. FLUJO DE INVITADOS

```
 Paso 1: Registro (Administrador/Registro)
   → Crear Persona (tipo_persona='INVITADO')
   → Crear perfil Invitado: entidad= "Alcaldía Riohacha", cargo="Secretario Educación"
   → Se genera automáticamente qr_token UUID
 Paso 2: Generar escarapela individual o por lote invitados
   → Mismo diseño pero badge naranja INVITADO
 Paso 3: Ingreso evento
   → Operador Asistencia escanea QR → VERDE (mismo flujo que aprendiz)
 Paso 4: Refrigerio
   → Por regla negocio: ¿corresponde entrega? Se define por evento/reglas
      (backend puede tener flag "invitado_tiene_refrigerio" en Evento)
 Paso 5: Certificado
   → Se entrega si cumple criterio; token de verificación público funciona igual
```

---

## 22. DISEÑO FUNCIONAL DEL DASHBOARD

### 22.1. 16 INDICADORES (KPIs en cards)

| # | Indicador | Color tarjeta header |
|---|---|---|
| 1 | Participantes registrados | #39A900 |
| 2 | Aprendices | #39A900 light |
| 3 | Instructores | #0067B1 |
| 4 | Invitados | #F57C00 |
| 5 | Proyectos | #39A900 |
| 6 | Instituciones Educativas | #424242 |
| 7 | Programas Técnicos | #424242 |
| 8 | Asistentes | #2E7D32 |
| 9 | Ausentes | #C62828 |
| 10 | % Asistencia | #2E7D32 |
| 11 | Refrigerios entregados / pendientes | #F9A825 |
| 12 | % Refrigerios entregados | #F9A825 |
| 13 | Certificados entregados | #39A900 |
| 14 | Certificados pendientes | #9E9E9E |
| 15 | % Certificados entregados | #39A900 |
| 16 | Operadores conectados (ahora) | #0067B1 |

### 22.2. 12 GRÁFICOS (Chart.js)

1. Barras: Participantes por Institución Educativa
2. Barras: Participantes por Programa Técnico
3. Barras: Proyectos por Institución
4. Barras: Proyectos por Programa Técnico
5. Barras horizontal: Participantes por Proyecto (top 15)
6. Barras horizontal: Participantes por Instructor
7. Doughnut: Distribución Aprendiz / Instructor / Invitado
8. Pie: Asistencia general (Asistió vs Ausente)
9. Barras apiladas: Asistencia por Institución
10. Barras apiladas: Asistencia por Programa
11. Barras agrupadas: Entrega de Refrigerios por tipo
12. Line/Radar: Entrega de certificados (tiempo)

### 22.3. 7 FILTROS (arriba del dashboard)
- Evento (select por nombre; por defecto = evento ACTIVO)
- Institución
- Municipio
- Programa técnico
- Proyecto
- Instructor
- Tipo de persona (todos / Aprendiz / Instructor / Invitado / Organizador)

### 22.4. ESTRATEGIA DE ACTUALIZACIÓN
- Componente JS en `static/js/dashboard.js`
- `setInterval(refrescarKPIs, 30000)` + `setInterval(refrescarGraficos, 60000)`
- Botón **GRANDE** `[ACTUALIZAR AHORA]` para manual
- Endpoints AJAX JSON:
  - GET `/dashboard/api/kpis/?evento=1&institucion=2&...`
  - GET `/dashboard/api/graficos/?tipo=participantes_x_institucion&...`

---

## 23. DISEÑO DE REPORTES

```
 reportes/
 ├── Excel (openpyxl)
 │    ├── participantes_evento_<id>.xlsx
 │    │     (Aprendices + Instructores + Invitados; pestañas separadas)
 │    ├── asistentes_evento.xlsx   (marcado fecha_hora)
 │    ├── ausentes_evento.xlsx     (N registrados que nunca asistieron)
 │    ├── refrigerios_evento.xlsx  (por tipo servicio + hora + operador)
 │    ├── certificados_evento.xlsx (código + token_verificación + entrega)
 │    ├── instituciones_consolidad.xlsx
 │    ├── programas_consolidado.xlsx
 │    ├── proyectos_detalle.xlsx (proyecto + institucion + instructor + lista aprendices)
 │    ├── instructor_consolidado.xlsx
 │    └── errores_importacion_<timestamp>.xlsx (fila, campo, valor, error, recomendación)
 │
 └── PDF (ReportLab)
      ├── reporte_general_ejecutivo_evento_<id>.pdf
      │    Portada con logo SENA + título + fecha
      │    Página 2: Consolidado numérico (los 16 KPIs en tabla)
      │    Páginas 3-5: Tablas por Institución / Programa / Proyecto
      │    Anexos: Top 10 proyectos por participación
      └── certificado_individual_<codigo>.pdf (pendiente diseño aprobado)
```

---

## 24. ESTRATEGIA IMPORTACIÓN EXCEL (openpyxl)

**Flujo de 4 pasos**:

```
 Paso 1: SUBIR ARCHIVO (plantilla definida por el sistema)
   Formulario con input file + selección:
    • Instituciones
    • Programas
    • Instructores
    • Proyectos
    • Participantes (Aprendices + Instructores + Invitados en una hoja)

 Paso 2: VALIDAR EN MEMORIA (NO guardar NADA aún en BD)
   ImportacionExcelService.validar(archivo, tipo):
     Recorre filas con openpyxl, registra cada fila en diccionario:
       clasificacion ∈ {VÁLIDO, ADVERTENCIA, ERROR, DUPLICADO}
       errores_por_fila = [ (campo, valor, mensaje, recomendacion) ... ]

   Validaciones comunes:
     • Identificación vacía o con formato no numérico (según Tipo ID)
     • Nombres / apellidos vacíos
     • Correo con regex rfc 5322 básico
     • Institución que no exista en catálogo → ERROR
     • Programa que no exista → ERROR
     • Instructor no existe → ERROR (o se crea automático con flag)
     • Fila exactamente igual a otra fila del Excel = DUPLICADO
     • Persona con mismo tipo_id + numero_id existente en BD = DUPLICADO (se puede actualizar o ignorar, según opción del usuario)

 Paso 3: PREVIEW (vista tabla HTML grande + badge por clasificación)
   Muestra:
     ✅ VÁLIDOS       (87 filas)
     ⚠️ ADVERTENCIAS  (5 filas)    (ej: correo sin dominio válido pero aceptable)
     ❌ ERRORES       (3 filas)    (NO se guardarán)
     🗂️ DUPLICADOS    (2 filas)    (ignorados o actualización)
   Botones:
     [CONFIRMAR IMPORTACIÓN] → solo guarda VÁLIDOS
     [DESCARGAR ERRORES.XLSX] → reporte completo con sugerencias
     [CANCELAR] → descarta todo

 Paso 4: CONFIRMACIÓN + GUARDADO + AUDITORÍA
   Dentro de transaction.atomic():
      - bulk_create / bulk_update (según opción)
      - AuditLog tipo IMPORT con datos de resumen JSON
```

---

## 25. ESTRATEGIA DE AUDITORÍA

```
 3 fuentes de captura (ninguna se olvida de la otra):

 ┌────────────────────────────────────────────────────────────┐
 │ 1. SEÑALES DJANGO (apps/*/signals.py)                      │
 │    post_save → si created → AuditLog ACCION=CREATE         │
 │    post_save → else → AuditLog ACCION=UPDATE (solo campos) │
 │    post_delete → AuditLog ACCION=DELETE                    │
 │   Decorador @receiver en modelos seleccionados:            │
 │   Persona, Aprendiz, Instructor, Invitado, Proyecto,      │
 │   Institucion, Programa, Evento, Usuario, TipoServicio     │
 └────────────────────────────────────────────────────────────┘

 ┌────────────────────────────────────────────────────────────┐
 │ 2. DECORADORES / MIXINS PERSONALIZADOS                     │
 │    @auditar(accion='IMPORT', modulo='instituciones')       │
 │    @auditar(accion='ASISTENCIA', modulo='asistencia')      │
 │    Capturan request.user, request.META['REMOTE_ADDR'],     │
 │    request.META.get('HTTP_USER_AGENT','')                  │
 └────────────────────────────────────────────────────────────┘

 ┌────────────────────────────────────────────────────────────┐
 │ 3. CUSTOM MIDDLEWARE en config/middleware.py               │
 │    class AuditoriaMiddleware:                               │
 │      Captura login/logout signals (user_logged_in)         │
 │      Almacena IP + user agent                               │
 └────────────────────────────────────────────────────────────┘

 PANEL ADMINISTRACIÓN / AUDITORÍA:
  Tabla filtrada: por usuario, acción, módulo, rango de fechas, entidad.
  Exportación a Excel.
```

---

## 26. ESTRATEGIA DE SEGURIDAD

| Riesgo | Medida |
|---|---|
| **CSRF** | `django.middleware.csrf.CsrfViewMiddleware` activo. Todos los formularios `{% csrf_token %}`. AJAX envía header `X-CSRFToken` desde cookie. 0 excepciones (incluso verificación pública certificados no acepta POST sin CSRF si requiere). |
| **XSS** | `autoescape` on por defecto en templates. `django-csp` CSP: `default-src 'self'`, `style-src 'self' 'unsafe-inline'`, `script-src 'self'`, `img-src 'self' data:`, `frame-ancestors 'none'`. Nunca marcar `|safe` sin sanitización `bleach`. |
| **Clickjacking** | `X-Frame-Options: DENY` + CSP frame-ancestors. |
| **HTTPS** | En producción `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000` (1 año), `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`. `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`. |
| **Contraseñas** | `PASSWORD_HASHERS` = Argon2 primary + PBKDF2 fallback. Validadores Django: min_length 10, común, numérico, similar user. |
| **Autenticación** | Login por username o email. 5 intentos fallidos → lock 30 min (middleware custom o `django-axes` sin dependencia extra). |
| **RBAC** | **TODOS** los endpoints sensibles usan `PermissionRequiredMixin` o `@permission_required`. URLs directas devuelven `403.html` (con mensaje institucional, sin stacktrace). |
| **PII minimización** | QR = UUID sin PII. Operador solo ve nombre+rol+institucion+proyecto. Pantalla busqueda oculta ultimos 4 digitos ID por defecto (flag admin para mostrar). |
| **File upload** | Whitelist extensiones: `.xlsx,.png,.jpg,.pdf`. Tamaño máx 10MB. `MEDIA_ROOT` sin ejecución (whitenoise no ejecuta, en PythonAnywhere static/media servidos sin handlers). |
| **Admin oculto** | `DJANGO_ADMIN_URL = config('DJANGO_ADMIN_URL', default='admin-seguro-sena-2026/')`. No usar `/admin/`. |
| **Rate limit** | Custom view decorator cache: `login/` 5 req/min por IP; endpoints AJAX QR: 60 req/min por usuario. |
| **Secretos** | `python-dotenv`; `.env` nunca en Git (`.gitignore`). En desarrollo `SECRET_KEY` local; en producción PythonAnywhere variable de entorno. |

---

## 27. ESTRATEGIA DE CONTINGENCIA

| # | Escenario | Procedimiento inmediato | Tiempo respuesta máx |
|---|---|---|---|
| C1 | **Falla de internet** en punto de ingreso | Usar teléfono con datos + hotspot secundario. Si no hay señal del todo: usar lista de asistencia IMPRESA (lote "Pendientes") + marcar a mano → luego cargar manualmente al sistema por ADMINISTRADOR (flag medio=MANUAL, comentario "contingencia C1"). | 5 min |
| C2 | **Falla de cámara** del operador | Cambiar a "BÚSQUEDA MANUAL" en la misma pantalla del operador → digitar número identificación o nombre → confirmar. Registra medio=MANUAL. | 1 min |
| C3 | **QR deteriorado** | A: Operador lee número manualmente (C2). B: ADMINISTRADOR reimprime escarapela desde módulo Escarapelas → nueva impresión. | 2 min |
| C4 | **Persona NO registrada** | Si está en Excel, REGISTRO crea Persona + Perfil → generar escarapela on the fly. Si NO está en fuente de verdad: **NO ingresar** al evento → remitir a puesto de registro. | 5-15 min |
| C5 | **Celular descargado / defectuoso** | Banco de 2 celulares de reserva por puesto. Cambiar SIM. Login con mismo usuario. | 3 min |
| C6 | **Caída temporal servidor PythonAnywhere** | Seguir C1 + C4: registros impresos físicos + bitácoras papel firmadas. Al restaurarse, ADMINISTRADOR carga lote manual con operador y hora real. | < 30 min |
| C7 | **Entrega duplicada sospechada (refrigerio)** | Consultar vista "Entregadas" por cédula. Si UniqueConstraint funcionó bien, no hay duplicidad. Si error humano (dos recibieron sin escanear la segunda): se marca en bitácora física + auditoría manual. | 2 min |
| C8 | **Error de operador (QR de otra persona)** | Retroceso por ADMINISTRADOR con permiso especial: elimina Asistencia/Entrega/Certificado + AuditLog DELETE. No accesible a operadores. | 1 min |
| C9 | **DDoS / tráfico malicioso** | Throttling rate limit en nginx PythonAnywhere + ban IP temporal. Cambio temporal `ALLOWED_HOSTS` + bloquear user agent. | < 5 min |

---

## 28. ESTRATEGIA PWA (Progressive Web App)

**Alcance controlado** (no sincroniza operaciones CRÍTICAS offline):

```
static/
├── manifest.json
├── service-worker.js
├── img/icons/
│   ├── icon-72x72.png
│   ├── icon-96x96.png
│   ├── icon-128x128.png
│   ├── icon-144x144.png
│   ├── icon-152x152.png
│   ├── icon-192x192.png
│   ├── icon-384x384.png
│   └── icon-512x512.png
└── img/splash/...

 manifest.json:
   - name: "Feria Proyectos Productivos SENA"
   - short_name: "Feria SENA"
   - start_url: "/?utm_source=pwa"
   - scope: "/"
   - display: "standalone"
   - orientation: "portrait"
   - background_color: "#FFFFFF"
   - theme_color: "#39A900"
   - icons: 7 tamaños + maskable

 service-worker.js estrategia:
   • precacheAppShell() al install: CSS principal, logo SENA, Work Sans fonts,
     html5-qrcode.min.js, chart.min.js
   • CacheFirst para CSS/JS/imagenes (estáticos - no cambian frecuentemente)
   • NetworkFirst para HTML de páginas (login, dashboard, vistas CRUD)
   • OFFLINE FALLBACK: "/offline/" página estática simple logo SENA +
     "Sin conexión. Favor comunicarse con el puesto de control."

   ⚠️ NO cachear POST /asistencia/api/registrar/ ni /refrigerios/api/entregar/
      → SIEMPRE van a red. Si fallan → mostrar offline y NO inventar registro.
```

---

## 29. ARQUITECTURA DESPLIEGUE PYTHONANYWHERE

**Ruta de archivos**:
```
/home/luisdiaz2026/
├── .virtualenvs/
│   └── feria_sena/          ← Python 3.10
└── feria_sena_proyecto/     ← git clone o upload
    ├── config/
    ├── apps/
    ├── manage.py
    ├── requirements.txt
    ├── venv  (NO, se usa el de .virtualenvs)
    ├── media/
    └── staticfiles/         ← collectstatic
```

**18 PASOS DEL PROMPT MAESTRO (reflejados en docs/PYTHONANYWHERE.md)**:

1. Crear cuenta PythonAnywhere (Beginner/Paid).
2. Crear nueva Web App: Manual configuration → Python 3.10.
3. Abrir Consola Bash.
4. `cd ~` + `git clone <repo>` o subir ZIP con FileZilla.
5. `mkvirtualenv feria_sena --python=/usr/bin/python3.10`
6. `workon feria_sena` + `cd ~/feria_sena_proyecto`
7. `pip install -r requirements.txt`
8. Crear `.env` con `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=luisdiaz2026.pythonanywhere.com`, etc.
9. Configurar WSGI: `/var/www/luisdiaz2026_pythonanywhere_com_wsgi.py` apunta a `config.wsgi.application`
10. `python manage.py check --deploy`
11. `python manage.py migrate`
12. `python manage.py createsuperuser`
13. `python manage.py collectstatic --noinput`
14. Configurar static alias: URL `/static/` → Path `/home/luisdiaz2026/feria_sena_proyecto/staticfiles/`
15. Configurar media alias: URL `/media/` → Path `/home/luisdiaz2026/feria_sena_proyecto/media/`
16. Habilitar HTTPS (Force HTTPS: on en Web Tab Security).
17. Probar lector QR: cámara requiere HTTPS.
18. Botón Reload Web App → listo.

**Backup diario automático**: script Bash `/home/luisdiaz2026/backup.sh` con:
```bash
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR
cp ~/feria_sena_proyecto/db.sqlite3 $BACKUP_DIR/db_$DATE.sqlite3
tar czf $BACKUP_DIR/media_$DATE.tar.gz ~/feria_sena_proyecto/media/
# Retener 14 días
find $BACKUP_DIR -type f -mtime +14 -delete
```
+ Scheduled Tasks todos los días 01:00 UTC.

---

## 30. ESTRUCTURA DEL REPOSITORIO

```
c:\Feria_2026\
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   ├── middleware.py            ← AuditoriaMiddleware
│   ├── context_processors.py    ← evento_activo, menu_dinamico_por_rol
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   └── validators.py
├── apps/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py · apps.py · urls.py
│   │   ├── views.py              ← Home, Offline, pública verificar certificado
│   │   ├── mixins.py             ← RoleRequiredMixin, AjaxPermissionRequiredMixin
│   │   ├── decorators.py         ← @role_required, @auditar, @ajax_login_required
│   │   ├── templatetags/
│   │   │   ├── __init__.py
│   │   │   ├── sena.py           ← {% has_group %}, {% badge_color %}
│   │   │   └── qr_tags.py
│   │   ├── utils.py              ← helpers fecha/hora CO, anonimizar cedula
│   │   └── services.py           ← AuditoriaService
│   ├── usuarios/
│   │   ├── models.py (Usuario)
│   │   ├── apps.py · admin.py · urls.py
│   │   ├── forms.py (CustomUserCreation/Change)
│   │   ├── views.py (CRUD usuarios + redirección login)
│   │   ├── signals.py (actualizar ultimo_acceso, crear perfil)
│   │   └── management/commands/
│   │       ├── crear_roles_iniciales.py
│   │       └── seed_demo.py     ← usuarios demo + datos demo (punto 34)
│   ├── eventos/ · personas/ · instituciones/ · programas/
│   ├── instructores/ · invitados/ · proyectos/
│   ├── escarapelas/ · asistencia/ · refrigerios/ · certificados/
│   ├── dashboard/  (views HTML + JSON API kpi/graficos + templatetags)
│   ├── reportes/   (ReportLab + openpyxl services)
│   └── auditoria/  (AuditLog model + admin + signals receivers)
├── templates/
│   ├── base.html
│   ├── base_operador.html
│   ├── 403.html · 404.html · 500.html · offline.html
│   ├── registration/login.html
│   ├── core/
│   ├── usuarios/
│   ├── eventos/
│   ├── proyectos/
│   ├── asistencia/ingreso.html
│   ├── refrigerios/entrega.html
│   ├── certificados/
│   │   ├── entrega.html
│   │   └── verificar_publico.html
│   ├── dashboard/dashboard.html
│   └── reportes/
├── static/
│   ├── css/
│   │   ├── sena.css  (variables :root { --sena-verde: #39A900; ...}, Work Sans)
│   │   └── sena.impresion.css  (@media print, escarapelas)
│   ├── js/
│   │   ├── app.js            (redirecciones, csrf token global)
│   │   ├── lector_qr.js      (html5-qrcode wrapper reusable: 3 modos: asis/refr/cert)
│   │   ├── dashboard.js      (fetch kpis + charts refresh)
│   │   ├── html5-qrcode.min.js
│   │   └── chart.umd.min.js
│   ├── img/
│   │   ├── logo-sena-verde.png
│   │   ├── logo-sena-blanco.png
│   │   ├── favicon.ico
│   │   └── icons/ (PWA)
│   ├── manifest.json
│   └── service-worker.js
├── media/
│   ├── qr/                 (auto: <uuid>.png por persona)
│   ├── escarapelas/        (temporales o generados on-demand)
│   ├── certificados/       (PDF almacenados si requerido)
│   ├── uploads/            (archivos excel importar)
│   └── .gitkeep
├── docs/
│   ├── ARQUITECTURA.md
│   ├── MODELO_DATOS.md
│   ├── ROLES_PERMISOS.md
│   ├── IDENTIDAD_VISUAL_SENA.md
│   ├── FASE0_ANALISIS_Y_ARQUITECTURA.md  ← ESTE DOCUMENTO
│   ├── INSTALACION_LOCAL.md
│   ├── PYTHONANYWHERE.md
│   ├── OPERACION_EVENTO.md
│   ├── SEGURIDAD.md
│   ├── PRUEBAS.md
│   └── PLAN_CONTINGENCIA.md
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── run_local.bat    (Windows: activa venv, runserver 0.0.0.0:8000)
```

---

## 31. DEPENDENCIAS PYTHON PROPUESTAS

| Paquete | Versión | Uso | ¿Compatible PythonAnywhere? |
|---|---|---|---|
| Django | 5.1.2 | Framework web | ✅ Sí |
| python-dotenv | 1.0.1 | Cargar .env | ✅ Sí |
| Pillow | 10.4.0 | Imágenes QR + logo | ✅ Sí |
| qrcode | 7.4.2 | Generar códigos QR PNG | ✅ Sí |
| openpyxl | 3.1.5 | Importar/exportar Excel | ✅ Sí |
| reportlab | 4.2.5 | PDF escarapelas, certificados, reportes | ✅ Sí |
| whitenoise | 6.7.0 | Servir static comprimido (sin nginx) | ✅ Sí |
| django-csp | 3.8 | Content Security Policy header | ✅ Sí |
| pandas | 2.3.3 | Análisis y validación datos importación | ✅ Sí |
| argon2-cffi | 23.1.0 | Hasheo contraseñas más seguro | ✅ Sí |

Dependencias JS (CDN o locales, NO npm):
- Bootstrap 5.3.x (CSS + JS Bundle con Popper)
- Chart.js 4.4.x
- html5-qrcode 2.x
- Work Sans (Google Fonts o self-hosted woff2)

---

## 32. RIESGOS TÉCNICOS

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **Concurrencia Refrigerios**: 2 operadores escanean al mismo tiempo misma persona → 2 entregas. | Media | ALTO | UniqueConstraint BD + `select_for_update` + `transaction.atomic` + catch IntegrityError. Prueba de concurrencia 100 hilos en FASE 19. |
| R2 | **QR ilegible**: papel mojado, QR roto, impresora baja calidad. | Media | Medio | Búsqueda manual contingency screen SIEMPRE visible + reimpresión rápida escarapela individual desde listado. |
| R3 | **Cámara no funciona por HTTPS**: en local http://192.168.x.x:8000 Chrome bloquea getUserMedia. | Alta | Medio | Documentar en INSTALACION_LOCAL: usar `localhost` (sí funciona) o generar certificado autofirmado `mkcert` + instrucciones. En producción: HTTPS PythonAnywhere incluido. |
| R4 | **Límites PythonAnywhere Free**: 100s CPU/día, 512MB storage. | Alta | Medio | Plan "Hacker" ($5/mes) recomendado para el día del evento. Agregar caché whitenoise para CPU. |
| R5 | **PDF escarapela pesado > 5MB con 500 personas**. | Media | Bajo | Optimizar QR PNG comprimido, incrustar solo 1 copia logo por PDF (no por página), usar TrueType Core fonts sin subir fuentes pesadas. Streaming HTTP response chunked. |
| R6 | **XSS / CSRF bypass**. | Baja | ALTO | 100% CSRF + CSP estricto + auditoría de seguridad manual + pruebas OWASP Top 10 (ZAP escaneo). |
| R7 | **Fuga PII**: URL /persona/<id>/ accesible por operador por URL guessing. | Baja | ALTO | Permisos a nivel vista. Búsquedas por `numero_identificacion` se hace con LIKE limitado al operador y devuelve SOLO nombre + iniciales. AuditLog registra cada consulta. |
| R8 | **Token UUID adivinable**. | Muy Baja | ALTO | UUID v4 (122 bits aleatorios), campo unique DB indexado. Brute force: 60 req/min rate limit → probabilidad = 0. |

---

## 33. PRUEBAS NECESARIAS (Django TestCase / pytest)

```
 tests/  (Django)
 ├── test_01_autenticacion.py
 │   ├── test_login_exitoso_admin
 │   ├── test_login_password_incorrecto
 │   ├── test_logout
 │   └── test_redirect_post_login_por_rol (5 casos)
 │
 ├── test_02_permisos_rbac.py  ← PRUEBA CRÍTICA
 │   ├── test_operador_asistencia_NO_puede_acceder_refrigerios → 403
 │   ├── test_operador_asistencia_NO_puede_acceder_certificados → 403
 │   ├── test_operador_refrigerio_NO_puede_administrar_usuarios → 403
 │   ├── test_operador_certificado_NO_puede_ver_dashboard_admin → 403
 │   └── test_usuario_consulta_NO_puede_POST_endpoints_cambios → 403
 │
 ├── test_03_catalogos.py
 │   ├── test_crud_institucion, test_crud_programa, test_crud_instructor
 │   └── test_importacion_instituciones_excel (25 filas)
 │
 ├── test_04_persona_qr.py
 │   ├── test_persona_qr_token_uuid_unico
 │   ├── test_persona_uq_tipo_numero_id
 │   └── test_qr_png_creado_automaticamente
 │
 ├── test_05_proyectos.py
 │   ├── test_crear_proyecto
 │   ├── test_uq_evento_codigo
 │   └── test_relacion_n_aprendices_por_proyecto
 │
 ├── test_06_asistencia.py  ← PRUEBA CRÍTICA DUPLICADOS
 │   ├── test_ingreso_primera_vez → VERDE created=True
 │   ├── test_ingreso_duplicado_mismo_evento → AMARILLO + IntegrityError atrapado
 │   └── test_busqueda_manual_contingencia → medio='MANUAL'
 │
 ├── test_07_refrigerios.py  ← PRUEBA CRÍTICA CONCURRENCIA
 │   ├── test_entrega_primera → VERDE
 │   ├── test_entrega_duplicada → AMARILLO
 │   ├── test_concurrencia_2_threads_mismo_refrigerio
 │   │   → transaction.TestCase + ThreadPoolExecutor(2)
 │   │   → assert EntregaServicio.objects.count() == 1
 │   └── test_cambio_servicio_activo
 │
 ├── test_08_certificados.py
 │   ├── test_entrega_duplicada_bloqueada
 │   ├── test_url_verificacion_publica → 200 + nombre visible
 │   └── test_url_verificacion_sin_pii → sin cédula ni correo
 │
 ├── test_09_importacion_excel.py
 │   ├── test_clasifica_validos_errores_duplicados
 │   ├── test_reporte_errores_xlsx
 │   └── test_commit_solo_validos
 │
 ├── test_10_reportes.py
 │   ├── test_reporte_excel_participantes (50 filas, openpyxl load)
 │   ├── test_reporte_pdf_ejecutivo (content_type pdf, size > 1KB)
 │   └── test_dashboard_kpis_sumatorias_coherentes
 │
 ├── test_11_auditoria.py
 │   └── test_post_save_crea_auditlog, test_login, test_import
 │
 └── test_12_busqueda_rapida.py
     ├── test_buscar_por_identificacion
     ├── test_buscar_por_nombre
     └── test_buscar_por_proyecto
```

---

## 34. PLAN DETALLADO IMPLEMENTACIÓN POR FASES (22)

| Fase | Objetivo | Entregable | Tiempo estimado |
|---|---|---|---|
| **FASE 0** | ✅ Análisis + Arquitectura (ESTE DOCUMENTO) | 36 puntos, 4 docs, FASE0 consolidado | 4 h |
| **FASE 1** | Creación proyecto Django estructura multi-settings | `config/`, `manage.py`, `apps/`, templates, static, settings base/dev/prod, `.env` | 1 h |
| **FASE 2** | Custom User + autenticación | `Usuario` model, login, seed_groups command, redirección por rol | 1.5 h |
| **FASE 3** | Roles y permisos | Groups Django + permissions + RoleRequiredMixin + matriz + tests RBAC 403 | 2 h |
| **FASE 4** | Modelo Persona CENTRAL + QR | `Persona`, `TipoIdentificacion`, `qr_token` UUID, imagen QR automática, vista previa | 2 h |
| **FASE 5** | Instituciones + Programas | `InstitucionEducativa`, `ProgramaTecnico`, CRUD CBV + plantillas Bootstrap + listados | 2 h |
| **FASE 6** | Instructores | `Instructor` (1:1 Persona), M2M programas, CRUD, importación | 1.5 h |
| **FASE 7** | Proyectos | `Proyecto`, CRUD, detalle, listado con filtros | 2 h |
| **FASE 8** | Aprendices + Invitados | `Aprendiz` (1:1 Persona + FK Proyecto), `Invitado`, asignación masiva | 2 h |
| **FASE 9** | Importación Excel | 4 pasos (cargar → validar → preview → confirmar), `errores_importacion.xlsx` | 3 h |
| **FASE 10** | QR sistema completo | Generación por persona, listado, vista individual, ZIP lote | 1 h |
| **FASE 11** | Escarapelas PDF ReportLab | Plantillas A6, lotes, diseño SENA, tests PDF válido | 3 h |
| **FASE 12** | Ingreso / Asistencia mobile-first | Lector html5-qrcode, AJAX, UQ, estados VERDE/AMARILLO/ROJO, búsqueda manual | 3 h |
| **FASE 13** | Refrigerios | TipoServicio, entrega, concurrencia transaction, tests 2 hilos | 2.5 h |
| **FASE 14** | Certificados + URL pública | Entrega QR, UQ, `/certificados/verificar/<token>/` | 2 h |
| **FASE 15** | Dashboard Chart.js | 16 KPIs, 12 gráficos, 7 filtros, AJAX polling 30 s | 4 h |
| **FASE 16** | Reportes Excel + PDF | 9 reportes Excel, PDF ejecutivo general | 3 h |
| **FASE 17** | Auditoría | Señales + decorators + middleware + panel + exportación Excel | 2 h |
| **FASE 18** | PWA | manifest.json + service-worker + offline fallback + iconos | 1.5 h |
| **FASE 19** | Pruebas automatizadas | ~50 tests Django, concurrencia, RBAC 403 | 3 h |
| **FASE 20** | PythonAnywhere despliegue | 18 pasos, SSL, collectstatic, backup script | 2 h |
| **FASE 21** | Prueba piloto 100 participantes | Flujo completo 5 dispositivos (1 asis, 2 refri, 1 certif, 1 admin) + correcciones | 4 h |
| **FASE 22** | Producción + datos reales + soporte | Migrar fichas INFORMACIÓN_POR_FICHA.xlsx reales, logo oficial, escarapelas aprobadas | 3 h |
| | | **Total estimado MVP completo** | **52 horas aprox.** |

---

## 35. CRITERIOS DE ACEPTACIÓN MVP (15 MEDIBLES)

El MVP se aprueba como TERMINADO solo si se cumplen TODOS:

- [ ] **CA-01** Se ejecuta el flujo end2end sin errores:
  - Admin crea Evento → Institución → Programa → Instructor → Proyecto → 3 Aprendices + 1 Invitado →
  - Admin imprime Escarapelas individuales →
  - Operador Asistencia escanea QR de 4 personas → VERDE x4 →
  - Vuelve a escanear una → AMARILLO (no crea segunda asistencia) →
  - Operador Refrigerio entrega almuerzo → 4 VERDES → 1 duplica AMARILLO →
  - Operador Certificado entrega 4 certificados → URL pública funciona sin login y SIN PII.
  - Dashboard muestra 4 asistentes, 4 refrigerios, 4 certificados.
  - Admin descarga reporte general.xlsx correcto.
- [ ] **CA-02** Existen 6 usuarios demo en desarrollo: admin_demo, registro_demo, asistencia_demo, refrigerio_demo, certificado_demo, consulta_demo (password documentado en seed_demo).
- [ ] **CA-03** Comando `python manage.py seed_demo` crea: ≥5 Instituciones, ≥5 Programas, ≥10 Instructores, ≥20 Proyectos, ≥100 Aprendices, ≥10 Invitados.
- [ ] **CA-04** Todo `Persona.qr_token` es único UUID v4. El PNG QR generado NO contiene cédula ni correo ni teléfono (leer contenido QR con scan offline: solo UUID).
- [ ] **CA-05** UniqueConstraints de AsistenciaEvento, EntregaServicio, Certificado existen en migraciones y NO en solo JS.
- [ ] **CA-06** Tests RBAC críticos pasan: 6 casos 403.
- [ ] **CA-07** PDF escarapela legible: nombre rol institucion proyecto QR (escanear QR manualmente devuelve a la persona correcta).
- [ ] **CA-08** Dashboard actualiza KPI de asistencia en menos de 32 s tras un nuevo registro, sin recargar manualmente.
- [ ] **CA-09** Importación Excel 100 filas sin errores: 100% guardado; 20 filas con errores: 20 NO guardados y errores.xlsx descargable con recomendación.
- [ ] **CA-10** Reportes Excel abren sin corromper en Microsoft Excel 2019+.
- [ ] **CA-11** AuditLog registra: login, logout, crear/modificar/eliminar Persona, Proyecto, importaciones, asistencia, refrigerios, certificados.
- [ ] **CA-12** Pantalla móvil 360×640: botón "Activar Cámara" visible sin scroll, área táctil ≥ 48×48 px, sin overflow horizontal.
- [ ] **CA-13** Verificación pública certificado /certificados/verificar/<token>/ no muestra cédula, teléfono, correo. Status 200 con sin login.
- [ ] **CA-14** Prueba concurrencia refrigerios: 2 hilos entregan mismo refrigerio misma persona → solo 1 fila en EntregaServicio.
- [ ] **CA-15** `python manage.py check --deploy` sin errores en settings.production (solo warnings no críticos permitidos).

---

## 36. INFORMACIÓN Y ARCHIVOS QUE NECESITO DE TI (LUIS FERMÍN) ANTES DE FASES AVANZADAS

| # | Item | ¿Disponible ahora? | Descripción |
|---|---|---|---|
| 1 | `logo-sena-verde.png` / `.svg` oficial | ❌ NO (adjuntado faltante) | Archivo original PNG/SVG logo SENA verde en alta resolución (≥ 2048 px). REQUERIDO para escarapelas PDF, certificados, header templates. EN EL PROMPT MAESTRO decía que se adjuntaba. FALTA. |
| 2 | Plantilla oficial de escarapela (Word/PDF) | ❌ NO | Si SENA Regional Guajira tiene una plantilla histórica de escarapela que debo respetar (tamaño, campos, colores por rol, código de barras, etc.), adjuntarla. Si NO existe, yo presento una propuesta y tú la apruebas antes de FASE 11. |
| 3 | Plantilla oficial certificado (Word/PDF) | ❌ NO | Análogo: ¿hay un pie de firma (Director Regional, Coordinador Articulación)? ¿Lugar y fecha con formato oficial? Si no existe, presento propuesta. |
| 4 | **Datos reales aprendices**: tipo + número identificación, nombres, apellidos, correo, teléfono (si disponible) por cada ficha 3161703... del Excel | ❌ NO | El Excel `INFORMACIÓN_POR_FICHA.xlsx` actual solo tiene Ficha, Programa, Institución, Grado, Municipio, Líder. NO tiene aprendices. Sin estos datos, el seed es DEMO. |
| 5 | **Datos reales Instructores** (líderes del Excel + otros): tipo identificación, número, correo, teléfono, foto (si se quiere) | ⚠️ Parcial (nombres de líderes sí están, sin datos de contacto) | Del Excel extraigo nombres líderes: SOREN ROMERO, YERLI ESPINOSA, ALEXANDRA CURIEL, ANDRES MEJIA, JAVIER RAMOS, DIOMEDES PEÑA, MARIA LOAIZA, RONALD CASTRILLON, JUAN MOLINA, YHIN VARGAS, ANDRES DAZA, PAOLA TORO, ALAN HENRRIQUEZ, HAMET BONIVENTO, ADRIAN ROSADO, ALEXANDER CHOLES, JAIME ARREGOCES, DORIXY DE ARMAS, GUILLERMO PAREJO, IVETH IMITOLA, JOSE MAESTRE, KATINA GOMEZ, MAR VELASQUEZ, YULYS CARPINTERO, GUSTAVO SEGRERA, JAIME SMITH, NEIL RAMIREZ, GIRIBERT REYES, etc. Falta identificación, correo, teléfono. |
| 6 | **Datos del evento piloto** (¿cuál feria en qué fecha?): Nombre, Fecha inicio y fin, Lugar exacto, Municipio, Regional por defecto | ❌ NO | Ej: "Feria Regional Proyectos Productivos Articulación Media 2026", 20 de noviembre 2026, Coliseo Cubierto de Riohacha, Riohacha, Guajira. |
| 7 | **Secretaría de Educación** por municipio (para llenar campo InstitucionEducativa.secretaria_educacion): ¿Riohacha = Secretaría Distrital? ¿Demás municipios = Secretaría Departamental de La Guajira? | ❌ NO | Si no lo especificas, asumo valor por defecto "Secretaría Departamental de Educación de La Guajira" y tú lo ajustas en el catálogo. |
| 8 | **Catálogo Tipos de Identificación** adicionales: ¿Solo TI, CC, PPT? O también RC (Registro Civil), CE (Cédula Extranjería), PAS (Pasaporte)? | ❌ NO | Definir antes de la importación real para no tener registros "Sin Tipo". |
| 9 | **Nombres y datos de Invitados confirmados** para la feria (institución, cargo). | ❌ NO | Se pueden ingresar manualmente en la semana previa al evento. |
| 10 | **Correos para operadores demo en el día piloto**: ¿Hay 5 celulares con sus respectivos correos/usuarios para montar Operador Asistencia x1, Operador Refrigerio x2, Operador Certificado x1, Admin x1? | ❌ NO | Útil para prueba piloto (FASE 21). |

---

## 🛑 FIN DE LA FASE 0 — PUNTO DE CONTROL

**Qué revisar tú (Luis Fermín) antes de aprobar y avanzar a FASE 1**:

1. [ ] Modelo Persona central aprobado (no 3 tablas separadas).
2. [ ] Matriz roles y permisos: OPERADOR_ASISTENCIA / REFRIGERIO / CERTIFICADO — acceso exclusivo a su módulo y búsqueda manual solamente.
3. [ ] UniqueConstraints correctos para no duplicar asistencia / refrigerio / certificado.
4. [ ] Estrategia concurrencia refrigerios (transaction + select_for_update) aceptada.
5. [ ] QR UUID opaco (sin PII) aceptado.
6. [ ] Arquitectura 16 apps Django aprobada o proponer consolidación.
7. [ ] Stack (SQLite + Django 5 + whitenoise + ReportLab) compatible con PythonAnywhere aceptado.
8. [ ] Información que me falta (lista punto 36) proporcionar o indicar qué asumir como demo.

Cuando respondas "Aprobado FASE 0" + lista de ajustes (si los hay), se inicia **FASE 1: Creación del proyecto Django**.
