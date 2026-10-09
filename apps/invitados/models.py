from django.db import models


class Invitado(models.Model):
    persona = models.OneToOneField(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='perfil_invitado',
    )
    entidad = models.CharField(max_length=200)
    cargo = models.CharField(max_length=150)

    @property
    def activo(self):
        try:
            from django.db import connection as _conn
            with _conn.cursor() as _cur:
                _cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s)",
                    ['invitados_invitado', 'activo']
                )
                _row = _cur.fetchone()
                if _row and _row[0]:
                    _cur.execute(
                        "SELECT activo FROM invitados_invitado WHERE id = %s LIMIT 1",
                        [self.pk]
                    )
                    _r2 = _cur.fetchone()
                    if _r2:
                        return bool(_r2[0])
        except Exception:
            pass
        return True

    @activo.setter
    def activo(self, valor):
        try:
            from django.db import connection as _conn
            with _conn.cursor() as _cur:
                _cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s)",
                    ['invitados_invitado', 'activo']
                )
                _row = _cur.fetchone()
                if _row and _row[0] and self.pk:
                    _cur.execute(
                        "UPDATE invitados_invitado SET activo = %s WHERE id = %s",
                        [bool(valor), self.pk]
                    )
        except Exception:
            pass

    def __str__(self):
        return str(self.persona)
