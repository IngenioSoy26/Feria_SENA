# SENA Feria 2026 · Control Operativo de Eventos

**Mobile-first · Django 5 · Configurable para CUALQUIER feria del SENA**
Regional Guajira · Programa Articulación con la Media Técnica

---

## 🎯 ¿Qué hace ESTE sistema? (¡NO es de evaluaciones ni de seguimiento!)

Es un **sistema operativo para el día de la feria**. Gestiona las 4 actividades críticas que requieren alta concurrencia y rapidez en celulares:

1. **📝 Registro unificado** de fichas, instituciones educativas, programa técnico, instructor líder, proyecto y **N aprendices dinámicos** en un solo wizard.
2. **✅ Control de asistencia por QR** — cada persona lleva un código QR UUID **opaco (sin datos personales)** en su escarapela; operadores móviles leen con la cámara del celular.
3. **🍴 Entrega de refrigerios (almuerzos)** con control de concurrencia estricto — **a la misma persona NO se le entrega 2 veces**, ni siquiera por 2 celulares que hagan clic al mismo tiempo (probado: 2 hilos simultáneos → 1 sola entrega VERDE + 1 AMARILLO/rechazo).
4. **🎓 Entrega de certificados de asistencia / participación** — código único verificable público (`SENA-{evento}-{persona}-{uuid8}`) + token_verificación UUID para consulta anónima de autenticidad.

Adicionalmente genera: **escarapelas A6 horizontal en PDF (con QR)** — listas para imprimir y cortar; **certificados PDF lote por grupo**; **dashboard KPI en tiempo real**; **auditoría completa de todo lo que pasa** (quién, cuándo, desde qué IP).

---

## ✨ Características diferenciales (para cualquier feria)

| Característica | Cómo se logra |
|---|---|
| **Configurable para cualquier feria** | Entidad `Evento` central con campo `activo`; tipos de servicio (almuerzos, refrigerios, kits, etc.) y roles creados **por comando**. |
| **Mobile-first de verdad** | Botones ≥48px; sin librerías pesadas; **lector QR html5-qrcode corre en Chrome/Android sin apps adicionales**; interfaz operador de 1 sola acción. |
| **Doble autenticación híbrida** | Operadores pueden **(a)** iniciar sesión tradicional **ó (b)** usar un enlace tokenizado público `/o/<TOKEN_OPERADORES>/...` — SIN CONTRASEÑA, ideal para celulares compartidos el día del evento. |
| **PII SIN salir en los QR** | QR NO codifica cédula/nombre/teléfono. Solo un UUID4. El backend hace la relación persona→UUID. Si pierden una escarapela, no hay filtración de datos. |
| **Unicidad garantizada en BD (no solo en código)** | 3 `UniqueConstraints` BD: Asistencia (evento,persona) · EntregaServicio (evento,persona,tipo) · Certificado (evento,persona). |
| **Registro descentralizado sin login** | Profesores/coordinadores desde el celular suben su ficha completa por `/r/<TOKEN_REGISTRO>/registro/` — sin crearles usuario. |
| **Totalmente parametrizable desde `.env`** | `MAX_APRENDICES_POR_PROYECTO` (1-99) · `TOKEN_REGISTRO` · `TOKEN_OPERADORES` · `ADMIN_URL` custom · `DATABASE_URL` switch SQLite↔Postgres. |
| **Seguridad lista para producción** | CSP estricto (django-csp) · CSRF global · contraseñas **Argon2** (no PBKDF2 débil) · `admin/` renombrado a ruta secreta · auditoría por signals + middleware. |

---

## 🧩 Módulos reales (lo que hoy EXISTE y funciona)

| Módulo | Ruta (login o token) | Qué hace |
|---|---|---|
| **Registro Wizard** | `/registro/` o `/r/<TOKEN_REGISTRO>/registro/` | Ficha 7 dígitos + Institución (deduplicada iexact) + Programa + Instructor Líder + Proyecto + 1..N aprendices. |
| **Operador Asistencia QR** | `/operador/asistencia/` o `/o/<TOKEN_OPERADORES>/asistencia/` | Cámara → lee QR → VERDE (ingresó) / AMARILLO (ya había ingresado). |
| **Operador Refrigerios** | `/operador/refrigerios/` o `/o/<TOKEN_OPERADORES>/refrigerios/` | Idem asistencia, pero contra `TipoServicio Almuerzo`. UniqueConstraint evita doble entrega. |
| **Operador Certificados** | `/operador/certificados/` o `/o/<TOKEN_OPERADORES>/certificados/` | Marca entrega + genera código único + token_verificación UUID. |
| **Escarapelas (individual / lote)** | `/escarapela/<persona_id>/` · `/escarapelas/lote/<grupo>/` | PDF A6 horizontal, logo SENA + nombre + rol + QR UUID. |
| **Certificados (editar + lote)** | `/certificado/editar/<id>/<tipo>/` · `/certificado/lote/<tipo>/<grupo>/` | Plantilla SENA código verificable. |
| **Dashboard KPI + gráficos** | `/dashboard/` · `/r/<TOKEN_REGISTRO>/dashboard/` | Total personas · Asistencia hoy · Refrigerios entregados · Top 5 municipios · Totales por rol (Chart.js). |
| **Listados CSV/Excel** | `/listados/<asistencia|refrigerios|certificados>/` | Exporta para imprimir/auditar. |
| **Panel Administrativo Django** | `/admin-seguro-sena-2026/` (configurable en `.env`) | CRUD completo entidades + auditoría. |

---

## 👥 Roles y permisos reales (6 grupos Django)

Creados por `python manage.py crear_roles_iniciales`:

| Rol | Acciones permitidas |
|---|---|
| **ADMINISTRADOR** | TODO: CRUD usuarios, roles, eventos, ver auditoría, dashboard completo, panel admin Django. |
| **REGISTRO** | Subir/editar fichas + proyectos + aprendices. Generar escarapelas lote. Ver dashboard. NO puede marcar refrigerios/certificados. |
| **OPERADOR_ASISTENCIA** | Solo panel asistencia QR. NO puede refrigerios. NO puede registro. |
| **OPERADOR_REFRIGERIO** | Solo panel refrigerios QR. 403 si intenta asistencia o certificados. |
| **OPERADOR_CERTIFICADO** | Solo panel entrega certificados. |
| **CONSULTA** | Ver listados y dashboard. POST y creación de entidades = 403. |

✅ Validado por tests `test_rbac_403.py`: 6/6 restricciones funcionan.

---

## 🔧 Stack Tecnológico

| Componente | Versión | Uso |
|---|---|---|
| Python | 3.10+ | Lenguaje (compatible Railway, PythonAnywhere, Ubuntu 22.04). |
| Django | 5.1.2 | Framework web MVT monolítico. |
| SQLite (dev) | - | Desarrollo local, 0 configuración. |
| PostgreSQL (prod) | ≥13 | Recomendado para Railway (SQLite NO soporta writes concurrentes de 6+ celulares). |
| Pillow | 10.4.0 | Procesamiento PNG escarapelas/logo. |
| qrcode | 7.4.2 | QR UUID4 opacos. |
| openpyxl | 3.1.5 | Lectura Excel carga fichas + exportar listados. |
| reportlab | 4.2.5 | PDF escarapelas A6 + certificados. |
| pandas | 2.3.3 | Estadísticas y grouping dashboard. |
| whitenoise | 6.7.0 | Estáticos comprimidos sin nginx (Railway/Render). |
| django-csp | 3.8 | Content Security Policy estricto anti-XSS. |
| argon2-cffi | 23.1.0 | Hashing contraseñas. |
| html5-qrcode (CDN) | 2.3.8 | Lector QR en navegador móvil sin App. |
| Chart.js (CDN) | 4.4.4 | Gráficos dashboard. |

---

## 📁 Estructura REAL del código (lo que está hoy en GitHub)

```
Feria_2026/
├── apps/                          # 16 aplicaciones Django (no hay app evaluaciones ni reportes separadas)
│   ├── usuarios/                  # Usuario custom + roles 6 grupos + comandos crear_roles_iniciales / seed_demo
│   ├── eventos/                   # Evento (activo feria actual), TipoIdentificacion, TipoServicio
│   ├── personas/                  # Persona + qr_token UUID (MODELO CENTRAL)
│   ├── instituciones/             # InstitucionEducativa (Municipio La Guajira 15 opciones)
│   ├── programas/                 # ProgramaTecnico
│   ├── instructores/              # Instructor 1:1 Persona
│   ├── invitados/                 # Invitado 1:1 Persona (entidades externas)
│   ├── proyectos/                 # Ficha (7 dígitos UQ) · Proyecto · Aprendiz 1:1 Persona → Proyecto
│   ├── asistencia/                # AsistenciaEvento + UQ(evento,persona)
│   ├── refrigerios/               # EntregaServicio + UQ(evento,persona,tipo_servicio)
│   ├── certificados/              # Certificado + UQ(evento,persona) + codigo_unico + token_verificacion
│   ├── escarapelas/               # Servicios generacion PDF individual/lote
│   ├── dashboard/                 # Vista dashboard completo (complementa simple/dashboard)
│   ├── auditoria/                 # AuditLog (actor,accion,modelo,ip,antes/despues) por signals
│   └── core/                      # ← LO MÁS USADO HOY: simple_views (wizard+operador+dashboard), mixins RBAC, simple_pdf
├── config/                        # settings/base.py · development.py · production.py · urls.py · wsgi.py · middleware propios
│   └── settings/
├── templates/                     # 16 plantillas HTML (login, base, 403/404/500, offline PWA)
│   └── simple/                    # Plantillas mobile-first 100% (home · wizard · operador · panel_admin · dashboard · listados · certificados)
├── static/                        # CÓDIGO FUENTE de CSS/JS/imágenes (NO lo borren!)
│   ├── css/sena.css               # Identidad visual SENA (verde #39A900 · amarillo #FFD100 · tipografía Ubuntu)
│   ├── img/logo-sena-verde.png    # Logo oficial SENA
│   ├── js/                        # app.js · dashboard.js · lector_qr.js · html5-qrcode.min.js · chart.umd.min.js
│   ├── manifest.json              # PWA básico (colores SENA, display standalone)
│   └── service-worker.js          # Cache estáticos + fallback offline.html
├── tests/                         # 3 archivos = 14 tests unitarios (ver abajo)
│   ├── test_autenticacion.py      # 7 tests auth/login/correo único/rol consulta
│   ├── test_rbac_403.py           # 6 tests restricciones RBAC 6 roles
│   └── test_concurrencia_refrigerios.py # 1 test CRÍTICO 2 hilos POST simultáneos = 1 VERDE + 1 AMARILLO
├── docs/                          # 6 documentos técnicos (ARQUITECTURA, MODELO_DATOS, ROLES_PERMISOS, etc.)
├── manage.py
├── requirements.txt               # 14 dependencias pin versionadas
├── .env.example                   # Plantilla variables de entorno (100% documentada)
└── .gitignore                     # NO sube .env / db.sqlite3 / venv / Excels datos brutos / PDF manuales / .trae/
```

---

## 🚀 Instalación local en 8 pasos

> Prerrequisitos: **Python 3.10–3.12** y **Git** instalados.

```bash
# 1. Clonar
git clone https://github.com/IngenioSoy26/Feria_SENA.git Feria_2026
cd Feria_2026

# 2. Entorno virtual (Windows PowerShell)
py -m venv venv
.\venv\Scripts\Activate.ps1
# Linux/mac: source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables entorno (plantilla)
copy .env.example .env   # Windows; en linux: cp .env.example .env
# Editar .env:
#   · DJANGO_SECRET_KEY  → generar una con:
#     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
#   · TOKEN_REGISTRO     → python -c "import secrets; print(secrets.token_urlsafe(18))"
#   · TOKEN_OPERADORES   → igual (token diferente al anterior)

# 5. Estructura BD
python manage.py migrate

# 6. Roles de sistema (obligatorio si no los crea migrate)
python manage.py crear_roles_iniciales

# 7. (Opcional) 6 usuarios demo + 5 instituciones + 5 programas + 1 evento activo + 20 aprendices
python manage.py seed_demo
# Contraseña de los 6 usuarios demo: DemoSena1234*

# 8. Servidor dev
python manage.py runserver 8000
```

Abrir http://localhost:8000 — si todo está bien, inicia sesión con `admin_demo / DemoSena1234*` y verás el **Panel Principal** con 4 tiles:
- Registro Fichas · Operador Asistencia · Operador Refrigerios · Operador Certificados

---

## 👤 Usuarios demo (generados por `seed_demo`)

Contraseña COMÚN: **`DemoSena1234*`**

| Usuario | Rol |
|---|---|
| `admin_demo` | ADMINISTRADOR · panel admin `/admin-seguro-sena-2026/` |
| `registro_demo` | REGISTRO |
| `asistencia_demo` | OPERADOR_ASISTENCIA |
| `refrigerio_demo` | OPERADOR_REFRIGERIO |
| `certificado_demo` | OPERADOR_CERTIFICADO |
| `consulta_demo` | CONSULTA (solo lecturas) |

---

## 📱 Rutas públicas tokenizadas (sin login — las que se comparten el día de la feria)

Editar TOKENs en `.env` y compartir solo estos enlaces (por WhatsApp a cada equipo):

```
# Equipo de inscripción / profesores:
https://<SU_DOMINIO>/r/feria-sena-registro-2026-facil-decidir/registro/

# Equipo PUERTA 1 (asistencia):
https://<SU_DOMINIO>/o/feria-sena-operadores-2026-operar-rapido/asistencia/

# Equipo COMEDOR (refrigerios):
https://<SU_DOMINIO>/o/feria-sena-operadores-2026-operar-rapido/refrigerios/

# Equipo ENTREGA CERTIFICADOS:
https://<SU_DOMINIO>/o/feria-sena-operadores-2026-operar-rapido/certificados/
```

⚠ Seguridad: si sospecha que un enlace se filtró, solo cambie el valor de `TOKEN_REGISTRO` o `TOKEN_OPERADORES` en el `.env` y reinicie el servidor — rutas retornarán 404 automáticamente.

---

## ✅ Pruebas unitarias (14 ejecutables, 100% pasan hoy)

```bash
cd Feria_2026
.\venv\Scripts\activate.ps1
python manage.py test tests -v 2
```

Resultado esperado (validado 2026-10-06):
```
Ran 14 tests in 0.97s
OK
```

| Suite | Tests | Cobertura crítica |
|---|---|---|
| `test_autenticacion.py` | 7 | login 200 · credenciales válidas 302 a home · credenciales malas 200 con error · no-auth 302 login · logout 302 · correo único · usuario nuevo asignado CONSULTA |
| `test_rbac_403.py` | 6 | Operador Asistencia 403 a refrigerios · Refrigerio 403 a certificados · Consulta 403 en POSTs |
| `test_concurrencia_refrigerios.py` | 1 | 2 ThreadPoolExecutor POST mismo QR al tiempo → exactamente 1 EntregaServicio creada + 1 respuesta AMARILLO/SQLITE_UQ |

---

## 🔒 Seguridad — checklist pre-despliegue (antes de publicar)

- [ ] `DEBUG=False` en `.env`
- [ ] `DJANGO_SECRET_KEY` no es la de `.env.example`
- [ ] `DJANGO_ALLOWED_HOSTS` = su dominio (NO `*`)
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://<dominio>`
- [ ] Base de datos: **Postgres Railway** (no SQLite para producción concurrente)
- [ ] `TOKEN_REGISTRO` y `TOKEN_OPERADORES` NO son los del repo público (ejecutar `secrets.token_urlsafe(18)`)
- [ ] **Eliminar** o **cambiar contraseñas** a los 6 usuarios `seed_demo`
- [ ] Comando `python manage.py check --deploy` = 0 warnings graves

---

## 📖 Documentación técnica interna

Todo está en la carpeta [docs/](docs/):

- 🏛 [ARQUITECTURA.md](docs/ARQUITECTURA.md) — decisiones de diseño, capas, middleware, CSP.
- 🗃 [MODELO_DATOS.md](docs/MODELO_DATOS.md) — entidades clave, UniqueConstraints transaccionales, Persona central.
- 🔐 [ROLES_PERMISOS.md](docs/ROLES_PERMISOS.md) — matriz completa funcionalidad × rol.
- 🎨 [IDENTIDAD_VISUAL_SENA.md](docs/IDENTIDAD_VISUAL_SENA.md) — paleta, tipografía, logo (conforme manual SENA 2024).
- 📋 [FASE0_ANALISIS_Y_ARQUITECTURA.md](docs/FASE0_ANALISIS_Y_ARQUITECTURA.md) — documento de aprobación inicial.
- ☁ [PYTHONANYWHERE.md](docs/PYTHONANYWHERE.md) — guía legacy despliegue PaaS (reemplazable por Railway).

---

## ☁ Despliegue Railway (RECOMENDADO — solicitado para el proyecto)

Archivos que deben crearse para Railway (próxima fase del roadmap):

```
Procfile  → web: gunicorn config.wsgi
requirements.txt  → agregar  gunicorn==22.0.0  psycopg2-binary==2.9.9
```

Variables Railway necesarias (Settings → Variables):
```
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<PROYECTO_RAILWAY>.up.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://<PROYECTO_RAILWAY>.up.railway.app
TOKEN_REGISTRO=...
TOKEN_OPERADORES=...
MAX_APRENDICES_POR_PROYECTO=3
# Railway inyecta automáticamente DATABASE_URL (Postgres)
```

---

## 🧪 Estado del desarrollo (Fases Reales)

| Fase | Estado | Descripción |
|---|---|---|
| ✅ F1 Análisis y requisitos | Completada | 5 doc técnicos aprobados. |
| ✅ F2 Modelado de datos | Completada | 16 modelos · 3 UniqueConstraint transaccionales · Persona central QR UUID. |
| ✅ F3 RBAC 6 roles | Completada | `crear_roles_iniciales` + `RoleRequiredMixin` · tests 6/6. |
| ✅ F4 Registro Wizard unificado | Completada | Ficha 7 dígitos · N aprendices dinámicos · deduplicación IE/Programa iexact. |
| ✅ F5 Asistencia / Refrigerios / Certificados QR | Completada | Operador mobile-first. UniqueConstraints + concurrencia probada. |
| ✅ F6 Escarapelas + Certificados PDF | Completada | ReportLab · A6 horizontal · Código verificación. |
| ✅ F7 Tokens públicos híbridos | Completada | `/r/<token>/registro` · `/o/<token>/<tipo>` — sin login. |
| ✅ F8 Seguridad hardening | Completada | Argon2 · CSP · admin renombrado · auditoría signals. |
| ✅ F9 Auditoría y tests | Completada | 14 tests unitarios · concurrencia 2 hilos. |
| ⚙ F10 Despliegue Railway | **En curso** | Procfile + gunicorn + psycopg2 + vars Railway. |

---

## 👨‍💻 Autor commit inicial

**Gustavo Segrera** · IngenioSoy26  
Repositorio público: <https://github.com/IngenioSoy26/Feria_SENA>  
Problemas/mejoras: abrir **Issue** en el repo.
