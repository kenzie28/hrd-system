from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0008_karyawan_kontrak_and_bpjs_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='jenis_kelamin',
            field=models.CharField(
                blank=True,
                choices=[('Perempuan', 'Perempuan'), ('Laki-Laki', 'Laki-Laki')],
                default='',
                max_length=9,
            ),
        ),
    ]
