from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0009_karyawan_jenis_kelamin'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='tanggal_kontrak_akhir',
            field=models.DateField(blank=True, null=True),
        ),
    ]
