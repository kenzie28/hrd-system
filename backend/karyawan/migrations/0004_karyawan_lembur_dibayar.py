from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0003_karyawan_gaji_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='lembur_dibayar',
            field=models.BooleanField(default=False),
        ),
    ]
