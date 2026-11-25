from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0011_karyawan_level_0_to_9'),
    ]

    operations = [
        migrations.RenameField(
            model_name='karyawan',
            old_name='kpj',
            new_name='no_kpj',
        ),
        migrations.AddField(
            model_name='karyawan',
            name='no_bpjs',
            field=models.CharField(blank=True, default='', max_length=16),
        ),
    ]
