from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0006_remove_karyawan_jumlah_anak_nikah'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='tanggal_lahir',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='tanggal_awal',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='tanggal_kontrak_awal',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='tanggal_keluar',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='percobaan_jabatan',
            field=models.BooleanField(default=False),
        ),
    ]
