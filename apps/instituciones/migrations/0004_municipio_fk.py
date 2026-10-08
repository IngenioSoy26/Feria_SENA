from django.db import migrations, models
import django.db.models.deletion


def migrar_municipios_char_a_fk(apps, schema_editor):
    InstitucionEducativa = apps.get_model('instituciones', 'InstitucionEducativa')
    Municipio = apps.get_model('instituciones', 'Municipio')
    cache_mun = {}
    qs = InstitucionEducativa.objects.order_by('pk')
    for ie in qs.iterator():
        mun_nombre_viejo = ''
        try:
            mun_nombre_viejo = (getattr(ie, 'municipio_texto', '') or '').strip().upper()
        except AttributeError:
            continue
        if not mun_nombre_viejo:
            continue
        if mun_nombre_viejo in cache_mun:
            mun_obj = cache_mun[mun_nombre_viejo]
        else:
            mun_obj, _ = Municipio.objects.get_or_create(
                nombre=mun_nombre_viejo,
                defaults={'departamento': 'LA GUAJIRA'}
            )
            cache_mun[mun_nombre_viejo] = mun_obj
        ie.municipio_fk = mun_obj
        ie.save(update_fields=['municipio_fk'])


def revertir_fk_a_char(apps, schema_editor):
    InstitucionEducativa = apps.get_model('instituciones', 'InstitucionEducativa')
    qs = InstitucionEducativa.objects.select_related('municipio_fk').order_by('pk')
    for ie in qs.iterator():
        if ie.municipio_fk_id:
            try:
                ie.municipio_texto = ie.municipio_fk.nombre
                ie.save(update_fields=['municipio_texto'])
            except AttributeError:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('instituciones', '0003_alter_institucioneducativa_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Municipio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('departamento', models.CharField(default='LA GUAJIRA', max_length=100, verbose_name='Departamento')),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Municipio',
                'verbose_name_plural': 'Municipios',
                'ordering': ['departamento', 'nombre'],
            },
        ),
        # Paso 1: agregar FK temporal nullable
        migrations.AddField(
            model_name='institucioneducativa',
            name='municipio_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='instituciones_temp',
                to='instituciones.municipio',
                verbose_name='Municipio (temporal)'
            ),
            preserve_default=False,
        ),
        # Paso 2: renombrar CharField viejo para copiar datos (municipio → municipio_texto)
        migrations.RenameField(
            model_name='institucioneducativa',
            old_name='municipio',
            new_name='municipio_texto',
        ),
        # Paso 3: copiar datos municipio_texto → FK Municipio (RunPython)
        migrations.RunPython(migrar_municipios_char_a_fk, revertir_fk_a_char),
        # Paso 4: eliminar el campo texto viejo
        migrations.RemoveField(
            model_name='institucioneducativa',
            name='municipio_texto',
        ),
        # Paso 5: renombrar FK temporal a nombre final municipio
        migrations.RenameField(
            model_name='institucioneducativa',
            old_name='municipio_fk',
            new_name='municipio',
        ),
        # Paso 6: cambiar FK a PROTECT y no-null
        migrations.AlterField(
            model_name='institucioneducativa',
            name='municipio',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='instituciones',
                to='instituciones.municipio',
                verbose_name='Municipio'
            ),
            preserve_default=False,
        ),
    ]
