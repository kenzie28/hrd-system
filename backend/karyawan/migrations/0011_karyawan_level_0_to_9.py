import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0010_karyawan_tanggal_kontrak_akhir'),
    ]

    operations = [
        migrations.AlterField(
            model_name='karyawan',
            name='level',
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(9),
                ]
            ),
        ),
    ]
