from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0007_karyawan_tanggal_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='status_kontrak',
            field=models.CharField(blank=True, default='', max_length=2),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='npwp',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='kpj',
            field=models.CharField(blank=True, default='', max_length=16),
        ),
        migrations.AddField(
            model_name='karyawan',
            name='tanggal_kpj',
            field=models.DateField(blank=True, null=True),
        ),
    ]
