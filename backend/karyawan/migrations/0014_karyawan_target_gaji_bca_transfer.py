from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0013_karyawan_absensi_dihitung'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='target_gaji',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='bca_transfer',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
