from django.db import migrations


def _sincronizar_correo_visible(apps, schema_editor):
    Persona = apps.get_model('personas', 'Persona')
    qs = Persona.objects.using(schema_editor.connection.alias).filter(tipo_persona='INSTRUCTOR')
    actualizados = 0
    for p in qs.iterator():
        mejor = (p.correo_sena or '').strip() or (p.correo_personal or '').strip() or None
        if not mejor:
            continue
        mejor = mejor.lower()
        actual = (p.correo or '').strip().lower()
        if actual != mejor:
            p.correo = mejor
            p.save(update_fields=['correo'])
            actualizados += 1


def _reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0004_persona_cargo_persona_entidad'),
    ]

    operations = [
        migrations.RunPython(
            code=_sincronizar_correo_visible,
            reverse_code=_reverse,
            atomic=False,
        ),
    ]
