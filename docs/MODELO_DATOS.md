# MODELO ENTIDAD-RELACIÓN — SENA FERIA PROYECTOS PRODUCTIVOS

---

## 1. VISIÓN GENERAL

El sistema gestiona la **Feria de Proyectos Productivos** del SENA, cubriendo:
- Autenticación y autorización de usuarios operativos.
- Catálogo de eventos por regional/municipio.
- Registro centralizado de personas (aprendices, instructores, invitados, organizadores).
- Proyectos, instituciones educativas y programas técnicos.
- Control de asistencia al evento.
- Entrega de servicios (refrigerios, almuerzos).
- Emisión y verificación de certificados.
- Auditoría de todas las operaciones sensibles.

---

## 2. DIAGRAMA CONCEPTUAL (TEXTO)

```
CustomUser ──────creado_por─────► Evento
                                     │
                                     ├─► Proyecto ──► InstitucionEducativa
                                     │              ├─► ProgramaTecnico
                                     │              └─► Instructor ──► Persona
                                     │
Persona (MODELO CENTRAL)             │
 ├─ Aprendiz ──► Proyecto            │
 ├─ Instructor ──► ProgramaTecnico   │
 └─ Invitado                         │
                                     │
Evento ──► AsistenciaEvento ◄── Persona (UNIQUE evento+persona)
Evento ──► TipoServicio
         └─► EntregaServicio ◄── Persona (UNIQUE evento+persona+tipo)
Evento ──► Certificado ◄── Persona (UNIQUE evento+persona)

AuditLog (entidad independiente, traza todo)
```

---

## 3. DESCRIPCIÓN DETALLADA DE ENTIDADES

---

### 3.1 CustomUser (Usuario del Sistema)

**Propósito:** Cuentas de operadores, administradores y personal que interactúa con el panel web/app.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint/autoincremental) | Identificador interno | PK, NOT NULL |
| `username` | VARCHAR(150) | Nombre de usuario para login | UNIQUE, NOT NULL |
| `email` | VARCHAR(254) | Correo corporativo/institucional | UNIQUE, NOT NULL |
| `nombres` | VARCHAR(100) | Nombres del usuario | NOT NULL |
| `apellidos` | VARCHAR(100) | Apellidos del usuario | NOT NULL |
| `rol` | ENUM/CHECK | `ADMINISTRADOR`, `OPERADOR`, `ORGANIZADOR_REGIONAL`, `AUDITOR`, `CONSULTA` | NOT NULL |
| `activo` | BOOLEAN | Indica si la credencial está habilitada | NOT NULL, DEFAULT TRUE |
| `ultimo_acceso` | DATETIME | Timestamp del último login exitoso | NULLABLE |
| `created_at` | DATETIME | Creación del registro | NOT NULL, DEFAULT NOW() |
| `updated_at` | DATETIME | Última modificación | NOT NULL, DEFAULT NOW() |

**UniqueConstraints:**
- `UQ_customuser_username` ON (`username`)
- `UQ_customuser_email` ON (`email`)

**Índices:**
- `IX_customuser_rol_activo` ON (`rol`, `activo`)

---

### 3.2 Evento

**Propósito:** Representa una Feria con sus datos de contexto geográfico y temporal.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) | Identificador del evento | PK, NOT NULL |
| `nombre` | VARCHAR(200) | Nombre oficial de la feria | NOT NULL |
| `descripcion` | TEXT | Resumen del evento, objetivos, temática | NULLABLE |
| `fecha_inicio` | DATETIME | Fecha y hora de apertura | NOT NULL |
| `fecha_fin` | DATETIME | Fecha y hora de cierre | NOT NULL |
| `lugar` | VARCHAR(250) | Nombre del recinto (CDI, auditorio, etc.) | NOT NULL |
| `municipio` | VARCHAR(100) | Municipio donde se realiza | NOT NULL |
| `regional` | VARCHAR(50) | Regional SENA (ej: Antioquia, Cundinamarca) | NOT NULL |
| `estado` | ENUM | `BORRADOR`, `PUBLICADO`, `EN_CURSO`, `FINALIZADO`, `CANCELADO` | NOT NULL, DEFAULT `BORRADOR` |
| `activo` | BOOLEAN | Borrado lógico | NOT NULL, DEFAULT TRUE |
| `creado_por` | FK → CustomUser | Usuario que creó el evento | NOT NULL |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_evento_nombre_regional_anio` ON (`nombre`, `regional`) — evita duplicar ferias iguales en la misma regional.

**Índices:**
- `IX_evento_fecha_inicio` ON (`fecha_inicio`)
- `IX_evento_regional_municipio` ON (`regional`, `municipio`)
- `IX_evento_estado` ON (`estado`)

---

### 3.3 Persona (MODELO CENTRAL)

**Propósito:** Registro único y canónico de toda persona física que interactúa con la feria (aprendiz, instructor, invitado, organizador).

#### Justificación del modelo centralizado Persona

Se elige una **única tabla Persona** con subtipado por relación (Aprendiz/Instructor/Invitado como tablas hijas con FK 1:1) por las siguientes razones técnicas y de negocio:

1. **Identidad única por individuo:** Un mismo número de identidad corresponde a una sola persona, aunque pueda desempeñar múltiples roles en diferentes ferias (ej: un instructor puede ser también invitado en una feria distinta, o un aprendiz pasar a ser invitado años después).
2. **Campos comunes:** Todos los tipos comparten identificación, nombres, apellidos, correo, teléfono, estado activo y token QR — no tiene sentido replicar estas columnas en tres tablas.
3. **QR tokenizado único:** El `qr_token` se asigna **por Persona**, no por rol. Así una credencial QR sirve para cualquier tipo de operación (asistencia, servicio, certificado) sin importar el rol que la persona tenga en un evento determinado.
4. **Integridad transaccional:** `AsistenciaEvento`, `EntregaServicio` y `Certificado` apuntan todos a la misma FK `persona_id`, garantizando que no haya asistencias duplicadas por estar registrados en varias tablas.
5. **Cumplimiento LOPD/GDPR (minimización):** Almacenar datos personales una sola vez reduce superficie de riesgo y simplifica solicitudes de eliminación/rectificación.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) | Id interno | PK, NOT NULL |
| `tipo_id` | VARCHAR(5) | Tipo de documento: `CC`, `TI`, `CE`, `PAS`, `NUIP`, `PEP` | NOT NULL |
| `numero_id` | VARCHAR(30) | Número de identificación | NOT NULL |
| `nombres` | VARCHAR(100) | Nombres completos | NOT NULL |
| `apellidos` | VARCHAR(100) | Apellidos completos | NOT NULL |
| `correo` | VARCHAR(254) | Correo personal | NULLABLE |
| `telefono` | VARCHAR(20) | Contacto telefónico | NULLABLE |
| `tipo_persona` | ENUM/SET | `APRENDIZ`, `INSTRUCTOR`, `INVITADO`, `ORGANIZADOR` | NOT NULL (permite múltiples roles si el motor lo soporta, o bien el rol se define por existencia en tabla hija). |
| `qr_token` | UUID | Token único por persona, NO contiene datos personales | UNIQUE, NOT NULL, DEFAULT uuid_generate_v4() |
| `activo` | BOOLEAN | Borrado lógico / inhabilitación | NOT NULL, DEFAULT TRUE |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_persona_tipo_id_numero_id` ON (`tipo_id`, `numero_id`) — una persona por documento.
- `UQ_persona_qr_token` ON (`qr_token`) — token QR irremplazable.

**Índices:**
- `IX_persona_tipo_persona_activo` ON (`tipo_persona`, `activo`)
- `IX_persona_apellidos_nombres` ON (`apellidos`, `nombres`) (para búsquedas manuales)

#### Cómo distinguir Aprendiz vs. Instructor vs. Invitado

La distinción se logra **por composición (FK 1:1)** y no por campo discriminador único, aunque `tipo_persona` sirve como hint de filtrado rápido:

| Rol | Cómo se distingue a nivel BD |
|---|---|
| **Aprendiz** | Existe un registro en tabla `Aprendiz` con `persona_id = Persona.id`. Se valida además que tenga una relación con `Proyecto`. |
| **Instructor** | Existe un registro en tabla `Instructor` con `persona_id = Persona.id`. Se valida además que tenga al menos una entrada en la tabla intermedia `Instructor_ProgramaTecnico`. |
| **Invitado** | Existe un registro en tabla `Invitado` con `persona_id = Persona.id`. Se valida además que `entidad` y `cargo` no estén vacíos. |
| **Organizador** | Se marca solo con `tipo_persona = 'ORGANIZADOR'` (no requiere tabla hija, sus atributos no difieren de Persona) |

Esta estrategia **permite que una persona tenga varios roles simultáneamente** (ej: Instructor en un proyecto y Organizador de la feria) sin perder la identidad única.

---

### 3.4 Aprendiz

**Propósito:** Extensión 1:1 de Persona para quienes presentan un proyecto productivo.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `persona_id` | FK → Persona |  | UNIQUE (1:1), NOT NULL |
| `proyecto_id` | FK → Proyecto | Proyecto que presenta | NOT NULL |
| `grado` | VARCHAR(50) | Etapa/nivel formativo (ej: "Etapa lectiva", "Etapa productiva", "Graduado") | NULLABLE |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_aprendiz_persona` ON (`persona_id`) — una persona no puede registrarse dos veces como aprendiz en la misma instancia (aunque sí puede participar en varios `Proyecto` a través de múltiples filas si el negocio lo requiere; en ese caso se elimina este UNIQUE y se agrega índice).

**Índices:**
- `IX_aprendiz_proyecto` ON (`proyecto_id`)

**Cardinalidades:**
- Persona (1) — (0..1) Aprendiz
- Proyecto (1) — (1..N) Aprendiz (un proyecto tiene varios aprendices expositores)

---

### 3.5 Instructor

**Propósito:** Extensión 1:1 de Persona para docentes/vinculados SENA.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `persona_id` | FK → Persona |  | UNIQUE (1:1), NOT NULL |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**Tabla intermedia ManyToMany:**

#### Instructor_ProgramaTecnico

| Campo | Tipo | Descripción |
|---|---|---|
| `instructor_id` | FK → Instructor | PK parte 1, NOT NULL |
| `programa_tecnico_id` | FK → ProgramaTecnico | PK parte 2, NOT NULL |

**UniqueConstraints:**
- `UQ_instructor_persona` ON (`persona_id`)
- PK compuesta `(instructor_id, programa_tecnico_id)`

**Cardinalidades:**
- Persona (1) — (0..1) Instructor
- Instructor (0..N) — (1..N) ProgramaTecnico  (un instructor maneja varios programas; un programa tiene varios instructores)

---

### 3.6 Invitado

**Propósito:** Extensión 1:1 de Persona para externos a la entidad.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `persona_id` | FK → Persona |  | UNIQUE (1:1), NOT NULL |
| `entidad` | VARCHAR(200) | Empresa, alcaldía, ONG, universidad... | NOT NULL |
| `cargo` | VARCHAR(150) | Función o rol dentro de la entidad | NOT NULL |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_invitado_persona` ON (`persona_id`)

**Cardinalidades:**
- Persona (1) — (0..1) Invitado

---

### 3.7 InstitucionEducativa

**Propósito:** CATÁLOGO — Institución (CIM, CDI, Sede, Aliado) que presenta proyectos.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `nombre` | VARCHAR(200) | Nombre oficial centro/institución | NOT NULL |
| `municipio` | VARCHAR(100) | Municipio sede principal | NOT NULL |
| `secretaria` | VARCHAR(100) | Secretaría de educación / instancia SENA | NULLABLE |
| `codigo` | VARCHAR(30) | Código Dane / Código SENA del centro | UNIQUE, NOT NULL |
| `activo` | BOOLEAN | Borrado lógico | NOT NULL, DEFAULT TRUE |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_institucion_codigo` ON (`codigo`)

**Índices:**
- `IX_institucion_municipio` ON (`municipio`)

---

### 3.8 ProgramaTecnico

**Propósito:** CATÁLOGO — Ofertas formativas SENA / programas técnicos.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `codigo` | VARCHAR(30) | Código único SENA del programa | UNIQUE, NOT NULL |
| `nombre` | VARCHAR(200) | Nombre del programa | NOT NULL |
| `activo` | BOOLEAN | Borrado lógico | NOT NULL, DEFAULT TRUE |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_programa_codigo` ON (`codigo`)

---

### 3.9 Proyecto

**Propósito:** Proyecto productivo inscrito en una feria específica.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `evento_id` | FK → Evento | Feria donde se presenta | NOT NULL |
| `codigo` | VARCHAR(50) | Código interno del proyecto | NOT NULL |
| `nombre` | VARCHAR(250) | Título del proyecto productivo | NOT NULL |
| `descripcion` | TEXT | Resumen, objetivo, impacto | NULLABLE |
| `institucion_id` | FK → InstitucionEducativa | Centro educativo que lo avala | NOT NULL |
| `programa_tecnico_id` | FK → ProgramaTecnico | Programa al que pertenece | NOT NULL |
| `instructor_responsable_id` | FK → Instructor | Docente responsable | NOT NULL |
| `estado` | ENUM | `INSCRITO`, `APROBADO`, `RECHAZADO`, `EXPONIENDO`, `PREMIADO`, `RETIRADO` | NOT NULL, DEFAULT `INSCRITO` |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_proyecto_evento_codigo` ON (`evento_id`, `codigo`) — código único por evento.

**Índices:**
- `IX_proyecto_evento_estado` ON (`evento_id`, `estado`)
- `IX_proyecto_institucion` ON (`institucion_id`)
- `IX_proyecto_instructor` ON (`instructor_responsable_id`)

**Cardinalidades:**
- Evento (1) — (1..N) Proyecto
- InstitucionEducativa (1) — (1..N) Proyecto
- ProgramaTecnico (1) — (0..N) Proyecto
- Instructor (1) — (1..N) Proyecto (como responsable)

---

### 3.10 AsistenciaEvento

**Propósito:** Registro único de ingreso de una persona a la feria.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `evento_id` | FK → Evento | Evento al que ingresa | NOT NULL |
| `persona_id` | FK → Persona | Quien ingresa | NOT NULL |
| `fecha_hora` | DATETIME | Marca temporal exacta de ingreso | NOT NULL, DEFAULT NOW() |
| `operador_id` | FK → CustomUser | Usuario que registró / validó | NOT NULL |
| `medio` | ENUM | `QR`, `MANUAL` | NOT NULL |

**UniqueConstraints (CLAVE DE NEGOCIO):**
- `UQ_asistencia_evento_persona` ON (`evento_id`, `persona_id`) — **una persona solo puede registrar asistencia UNA vez por evento.**

**Índices:**
- `IX_asistencia_fecha_hora` ON (`fecha_hora`)
- `IX_asistencia_operador` ON (`operador_id`)

**Cardinalidades:**
- Evento (1) — (0..N) AsistenciaEvento
- Persona (1) — (0..N) AsistenciaEvento  (varias ferias distintas)
- CustomUser (1) — (0..N) AsistenciaEvento  (operador)

---

### 3.11 TipoServicio

**Propósito:** CATÁLOGO de servicios entregables durante el evento.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `evento_id` | FK → Evento | Evento donde aplica este servicio | NOT NULL |
| `nombre` | VARCHAR(100) | `Refrigerio mañana`, `Almuerzo`, `Refrigerio tarde` (catálogo cerrado por evento) | NOT NULL |
| `activo` | BOOLEAN | Si se sigue entregando | NOT NULL, DEFAULT TRUE |
| `created_at` | DATETIME |  | NOT NULL |
| `updated_at` | DATETIME |  | NOT NULL |

**UniqueConstraints:**
- `UQ_tipo_servicio_evento_nombre` ON (`evento_id`, `nombre`) — un nombre de servicio no se repite en el mismo evento.

**Cardinalidades:**
- Evento (1) — (1..N) TipoServicio

---

### 3.12 EntregaServicio

**Propósito:** Registro de que a una persona se le entregó determinado servicio en un evento concreto, sin duplicados.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `evento_id` | FK → Evento |  | NOT NULL |
| `persona_id` | FK → Persona |  | NOT NULL |
| `tipo_servicio_id` | FK → TipoServicio |  | NOT NULL |
| `fecha_hora` | DATETIME | Instante de entrega | NOT NULL, DEFAULT NOW() |
| `operador_id` | FK → CustomUser | Quién registró | NOT NULL |
| `medio` | ENUM | `QR`, `MANUAL` | NOT NULL |

**UniqueConstraints (CLAVE DE NEGOCIO — TRIPLE):**
- `UQ_entrega_servicio_evento_persona_tipo` ON (`evento_id`, `persona_id`, `tipo_servicio_id`) — una persona NO puede recibir el mismo tipo de servicio más de una vez por evento.

**Índices:**
- `IX_entrega_servicio_fecha_hora` ON (`fecha_hora`)
- `IX_entrega_servicio_operador` ON (`operador_id`)

**Cardinalidades:**
- Evento (1) — (0..N) EntregaServicio
- Persona (1) — (0..N) EntregaServicio
- TipoServicio (1) — (0..N) EntregaServicio
- CustomUser (1) — (0..N) EntregaServicio

---

### 3.13 Certificado

**Propósito:** Emisión de certificado digital único por evento + persona.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `evento_id` | FK → Evento | Evento por el que se certifica | NOT NULL |
| `persona_id` | FK → Persona | Certificado a | NOT NULL |
| `codigo_unico` | VARCHAR(60) | Código legible humano para impresión (ej: `FPP-2026-ANT-000452`) | UNIQUE, NOT NULL |
| `fecha_hora_entrega` | DATETIME | Fecha en que se emitió/descargó | NOT NULL, DEFAULT NOW() |
| `operador_id` | FK → CustomUser | Quién autorizó la emisión | NOT NULL |
| `medio` | ENUM | `QR`, `MANUAL`, `AUTOMATICO` | NOT NULL |
| `token_verificacion` | UUID | Token público de verificación en portal | UNIQUE, NOT NULL, DEFAULT uuid_generate_v4() |

**UniqueConstraints (CLAVE DE NEGOCIO):**
- `UQ_certificado_evento_persona` ON (`evento_id`, `persona_id`) — una persona recibe UNO y solo UN certificado por evento.
- `UQ_certificado_codigo_unico` ON (`codigo_unico`)
- `UQ_certificado_token_verificacion` ON (`token_verificacion`)

**Cardinalidades:**
- Evento (1) — (0..N) Certificado
- Persona (1) — (0..N) Certificado  (por eventos distintos)
- CustomUser (1) — (0..N) Certificado

---

### 3.14 AuditLog

**Propósito:** Registro inmutable de auditoría para operaciones sensibles (crear/editar/eliminar entidades, acceso, emisiones). Optimizado para escritura masiva.

| Campo | Tipo | Descripción | Restricciones |
|---|---|---|---|
| `id` | PK (bigint) |  | PK, NOT NULL |
| `usuario` | VARCHAR(150) | username del CustomUser (se duplica por si acaso se elimina la cuenta) | NOT NULL |
| `accion` | ENUM/VARCHAR(30) | `CREATE`, `READ`, `UPDATE`, `DELETE`, `LOGIN`, `LOGIN_FAIL`, `EXPORT`, `PRINT_CERT`, `QR_SCAN` | NOT NULL |
| `modulo` | VARCHAR(100) | `USUARIOS`, `EVENTOS`, `PERSONAS`, `PROYECTOS`, `ASISTENCIA`, `SERVICIOS`, `CERTIFICADOS`, `SISTEMA` | NOT NULL |
| `entidad` | VARCHAR(100) | Nombre tabla/entidad afectada | NULLABLE |
| `id_entidad` | BIGINT | Id de la entidad afectada | NULLABLE |
| `datos_json` | JSON/JSONB | Antes/después, payload, cambios | NULLABLE |
| `fecha_hora` | DATETIME |  | NOT NULL, DEFAULT NOW() |
| `ip` | VARCHAR(45) | IPv4 o IPv6 del cliente | NULLABLE |

**Índices (PARTICIONADO recomendado por fecha en motores de gran volumen):**
- `IX_audit_fecha_hora` ON (`fecha_hora` DESC)
- `IX_audit_usuario_fecha` ON (`usuario`, `fecha_hora` DESC)
- `IX_audit_modulo_accion` ON (`modulo`, `accion`)
- `IX_audit_entidad_id` ON (`entidad`, `id_entidad`)

**Observaciones de seguridad:**
- Sin FK, sin ON DELETE CASCADE — la tabla es inmutable y sobrevive incluso si se eliminan las entidades que registra.
- Sin constraints UNIQUE — cada inserción es un suceso único con timestamp.

---

## 4. ESTRATEGIA QR TOKENIZADO (SIN DATOS PERSONALES)

### 4.1 Principio

El código QR **nunca contiene PII** (datos de identificación personal: cédula, nombres, correo). Solo contiene un **UUID aleatorio (v4)** que actúa como token opaco.

### 4.2 Contenido exacto del QR

El QR almacena un JSON mínimo:

```json
{
  "v": 1,
  "t": "550e8400-e29b-41d4-a716-446655440000"
}
```

Donde:
- `v` = versión de protocolo QR (permite evolucionar sin romper lectores antiguos).
- `t` = `qr_token` de la tabla `Persona` (UUID v4, 128 bits de entropía, impredecible).

### 4.3 Flujo operativo de lectura QR

1. El lector (app móvil/web) escanea el QR y extrae el token.
2. El backend recibe `POST /api/qr/lookup { token: "<uuid>" }`.
3. Resuelve internamente: `Persona WHERE qr_token = <uuid> AND activo = TRUE`.
4. Retorna **solo la información necesaria para la operación en curso**:
   - Si es asistencia → nombres resumidos, tipo de persona, estado.
   - Si es servicio → lista de servicios ya entregados vs. pendientes.
   - Si es certificado → valida si ya fue emitido o no.
5. El lector NUNCA ve ni cédula ni correo ni teléfono a menos que la operación lo requiera explícitamente.

### 4.4 Ventajas de seguridad / cumplimiento

- **No hay que regenerar QRs si cambian datos de la persona** (correo, teléfono, grado) — el token sigue siendo válido.
- **Fuga de un QR no compromete identidad**: solo una UUID sin contexto.
- **Fácil revocación**: si una credencial se pierde, basta con asignar un nuevo `qr_token` a la persona y marcar el viejo como revocado (o usar versión con columna `qr_token_revocados` si se necesita historial).
- **Cumple principio de menor conocimiento (least privilege)**: el lector de campo no necesita acceso a la tabla completa de personas.

### 4.5 Rotación/regeneración del token

- Operación administrativa: `POST /api/personas/{id}/rotar-qr`
- Genera nueva UUID v4, actualiza `Persona.qr_token`, registra `AuditLog(accion='QR_ROTATE', entidad='Persona', id_entidad={id})`.
- El token anterior queda invalidado inmediatamente.

---

## 5. RESUMEN DE CARDINALIDADES Y RELACIONES

| Relación | Cardinalidad |
|---|---|
| CustomUser → Evento (creado_por) | 1:N |
| Evento → Proyecto | 1:N |
| Persona → Aprendiz (FK) | 1:0..1 |
| Persona → Instructor | 1:0..1 |
| Persona → Invitado | 1:0..1 |
| Aprendiz → Proyecto | N:1 |
| Instructor ↔ ProgramaTecnico | M:N (tabla intermedia) |
| Proyecto → InstitucionEducativa | N:1 |
| Proyecto → ProgramaTecnico | N:1 |
| Proyecto → Instructor (responsable) | N:1 |
| AsistenciaEvento → Evento + Persona | (Evento, Persona) UNIQUE |
| TipoServicio → Evento | N:1 |
| EntregaServicio → Evento + Persona + TipoServicio | (Evento, Persona, TipoServicio) UNIQUE |
| Certificado → Evento + Persona | (Evento, Persona) UNIQUE |
| AuditLog → (independiente) | N/A |

---

## 6. UNIQUE CONSTRAINTS — RESUMEN CONSOLIDADO

| Tabla | Constraint | Columnas |
|---|---|---|
| CustomUser | UQ_customuser_username | `username` |
| CustomUser | UQ_customuser_email | `email` |
| Evento | UQ_evento_nombre_regional | `nombre`, `regional` |
| Persona | UQ_persona_documento | `tipo_id`, `numero_id` |
| Persona | UQ_persona_qr_token | `qr_token` |
| Aprendiz | UQ_aprendiz_persona | `persona_id` |
| Instructor | UQ_instructor_persona | `persona_id` |
| Invitado | UQ_invitado_persona | `persona_id` |
| InstitucionEducativa | UQ_institucion_codigo | `codigo` |
| ProgramaTecnico | UQ_programa_codigo | `codigo` |
| Proyecto | UQ_proyecto_evento_codigo | `evento_id`, `codigo` |
| **AsistenciaEvento** | **UQ_asistencia_evento_persona** | **`evento_id`, `persona_id`** |
| TipoServicio | UQ_tipo_servicio_evento_nombre | `evento_id`, `nombre` |
| **EntregaServicio** | **UQ_entrega_servicio_unica** | **`evento_id`, `persona_id`, `tipo_servicio_id`** |
| **Certificado** | **UQ_certificado_evento_persona** | **`evento_id`, `persona_id`** |
| Certificado | UQ_certificado_codigo | `codigo_unico` |
| Certificado | UQ_certificado_token | `token_verificacion` |

---

## 7. RECOMENDACIONES DE IMPLEMENTACIÓN

1. **Motor BD sugerido:** PostgreSQL 15+ por soporte nativo UUID, JSONB (para `AuditLog.datos_json`), ENUMs nativos y particionamiento de tablas por fecha.
2. **Soft delete generalizado:** todas las entidades de negocio llevan `activo BOOLEAN DEFAULT TRUE` en lugar de `DELETE` físico, a excepción de tablas transaccionales como `AsistenciaEvento`, `EntregaServicio`, `Certificado` y `AuditLog`, que son inmutables.
3. **Extensión `pgcrypto`** para `uuid_generate_v4()` o uso de `gen_random_uuid()` nativo en PostgreSQL 13+.
4. **Particionar AuditLog** por `fecha_hora` (mensual o trimestral) para mantener consultas rápidas al crecer el volumen.
5. **Aplicar CHECK en rangos:** `fecha_fin > fecha_inicio` en Evento y Proyecto.
6. **Roles de BD:** `rol_aplicacion` (CRUD tablas negocio), `rol_auditor` (solo SELECT en AuditLog + tablas de lectura), `rol_admin` (DDL + rotación tokens).
