"""
RESCATE SQL INVERSO V38.2 (VUELTA A V38.1 DESPUÉS DE REVERTIR V39).

Propósito:
  En V39 eliminamos columnas legacy 'nombres' y 'apellidos' de la tabla BD
  'usuarios_usuario' (mediante _rescate_sql.py Paso 4 + migración 0004), porque
  en arquitectura V39 eran @property desde Persona.

  Ahora volvimos a V38.1, donde el modelo Usuario SÍ tiene los fields
  'nombres' y 'apellidos' como CharField NORMALES. Pero en Railway Postgres,
  las columnas físicas YA NO EXISTEN → ProgrammingError:
    column usuarios_usuario.nombres does not exist
    LINE 1: ..."usuarios_usuario"."email", "usuarios_usuario"."nombres", ...

SOLUCIÓN (idempotente, NUNCA falla):
  1) CREAR columna 'nombres' IF NOT EXISTS varchar(150) NOT NULL DEFAULT ''
  2) CREAR columna 'apellidos' IF NOT EXISTS varchar(150) NOT NULL DEFAULT ''
  3) POPULATE con first_name UPPER → nombres, last_name UPPER → apellidos
     donde esas columnas estaban vacías (para respetar los AbstractUser fields).

Ejecutado desde 3 puntos como el rescate original V39:
  · apps.usuarios.apps.UsuariosConfig.ready()
  · config/wsgi.py antes de get_wsgi_application()
  · config/asgi.py antes de get_asgi_application()
"""
import sys


def SQL_recrear_nombres_apellidos_si_no_existen():
    """Paso único: crear columns legacy + populate con first_name / last_name."""
    try:
        from django.db import connection as _conn
        _vendor = str(getattr(_conn, 'vendor', '') or '').lower()
        try:
            _conn.ensure_connection()
        except Exception:
            pass

        if 'postgres' in _vendor:
            # 1) Crear columna nombres IF NOT EXISTS
            try:
                with _conn.cursor() as cur:
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'usuarios_usuario'
                                  AND column_name = 'nombres'
                            ) THEN
                                ALTER TABLE "usuarios_usuario"
                                    ADD COLUMN "nombres"
                                    varchar(150) NOT NULL DEFAULT '';
                            END IF;
                        END$$;
                    """)
                    _conn.commit() if hasattr(_conn, 'commit') else None
            except Exception as ex:
                print(f"[RESCATE_V38] add nombres: {ex}", file=sys.stderr)

            # 2) Crear columna apellidos IF NOT EXISTS
            try:
                with _conn.cursor() as cur:
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'usuarios_usuario'
                                  AND column_name = 'apellidos'
                            ) THEN
                                ALTER TABLE "usuarios_usuario"
                                    ADD COLUMN "apellidos"
                                    varchar(150) NOT NULL DEFAULT '';
                            END IF;
                        END$$;
                    """)
                    _conn.commit() if hasattr(_conn, 'commit') else None
            except Exception as ex:
                print(f"[RESCATE_V38] add apellidos: {ex}", file=sys.stderr)

            # 3) Populate nombres/apellidos (vacíos) desde first_name / last_name
            try:
                with _conn.cursor() as cur:
                    cur.execute("""
                        UPDATE "usuarios_usuario"
                        SET "nombres" = CASE
                            WHEN COALESCE(TRIM("nombres"), '') = ''
                                 AND COALESCE(TRIM("first_name"), '') <> ''
                            THEN UPPER(TRIM("first_name"))
                            ELSE "nombres"
                        END,
                        "apellidos" = CASE
                            WHEN COALESCE(TRIM("apellidos"), '') = ''
                                 AND COALESCE(TRIM("last_name"), '') <> ''
                            THEN UPPER(TRIM("last_name"))
                            ELSE "apellidos"
                        END
                        WHERE COALESCE(TRIM("nombres"), '') = ''
                           OR COALESCE(TRIM("apellidos"), '') = '';
                    """)
                    _conn.commit() if hasattr(_conn, 'commit') else None
            except Exception as ex:
                print(f"[RESCATE_V38] populate nombres/apellidos: {ex}", file=sys.stderr)
        else:
            # SQLite dev local
            try:
                with _conn.cursor() as cur:
                    cur.execute("PRAGMA table_info('usuarios_usuario');")
                    cols = [str(r[1]).lower() for r in cur.fetchall()]
                    if 'nombres' not in cols:
                        cur.execute(
                            'ALTER TABLE "usuarios_usuario" '
                            'ADD COLUMN "nombres" varchar(150) NOT NULL DEFAULT \'\';'
                        )
                        _conn.commit() if hasattr(_conn, 'commit') else None
                    cur.execute("PRAGMA table_info('usuarios_usuario');")
                    cols2 = [str(r[1]).lower() for r in cur.fetchall()]
                    if 'apellidos' not in cols2:
                        cur.execute(
                            'ALTER TABLE "usuarios_usuario" '
                            'ADD COLUMN "apellidos" varchar(150) NOT NULL DEFAULT \'\';'
                        )
                        _conn.commit() if hasattr(_conn, 'commit') else None
                    try:
                        cur.execute("""
                            UPDATE "usuarios_usuario"
                            SET "nombres" = CASE
                                WHEN COALESCE(TRIM("nombres"), '') = ''
                                     AND COALESCE(TRIM("first_name"), '') <> ''
                                THEN UPPER(TRIM("first_name"))
                                ELSE "nombres"
                            END,
                            "apellidos" = CASE
                                WHEN COALESCE(TRIM("apellidos"), '') = ''
                                     AND COALESCE(TRIM("last_name"), '') <> ''
                                THEN UPPER(TRIM("last_name"))
                                ELSE "apellidos"
                            END
                            WHERE COALESCE(TRIM("nombres"), '') = ''
                               OR COALESCE(TRIM("apellidos"), '') = '';
                        """)
                        _conn.commit() if hasattr(_conn, 'commit') else None
                    except Exception:
                        pass
            except Exception as ex:
                print(f"[RESCATE_V38] sqlite nombres/apellidos: {ex}", file=sys.stderr)
        return True
    except Exception as e:
        try:
            print(f"[RESCATE_V38] fallo general: {e}", file=sys.stderr)
        except Exception:
            pass
        return False


def SQL_ELIMINAR_UNIQUE_EMAIL_SI_EXISTE_V38():
    """
    Opcional V38.2: En V39.4/V39.7 dropeamos UNIQUE constraint de email para
    evitar duplicate key al asociar Admin legacy con Persona misma correo.
    Aunque en V38.1 sí era UNIQUE, lo mantenemos dropeado si existiera
    para evitar IntegrityError cuando un usuario sin correo y otro iguales
    (permitimos mas flexibilidad en V38.2 también).
    """
    try:
        from django.db import connection as _conn
        _vendor = str(getattr(_conn, 'vendor', '') or '').lower()
        if 'postgres' in _vendor:
            try:
                with _conn.cursor() as cur:
                    cur.execute("""
                        ALTER TABLE "usuarios_usuario"
                        DROP CONSTRAINT IF EXISTS "usuarios_usuario_email_key";
                    """)
                    _conn.commit() if hasattr(_conn, 'commit') else None
            except Exception:
                pass
            try:
                with _conn.cursor() as cur:
                    cur.execute('DROP INDEX IF EXISTS "usuarios_usuario_email_key";')
                    _conn.commit() if hasattr(_conn, 'commit') else None
            except Exception:
                pass
        return True
    except Exception:
        return False


def SQL_EJECUTAR_RESCATES_V38():
    """Ejecuta todos los rescates inverso V38 en orden; nunca raise."""
    try:
        SQL_recrear_nombres_apellidos_si_no_existen()
    except Exception:
        pass
    try:
        SQL_ELIMINAR_UNIQUE_EMAIL_SI_EXISTE_V38()
    except Exception:
        pass
    return True
