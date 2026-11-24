import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gaji', '0003_gaji_proses_job'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gaji',
            name='level',
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(9),
                ]
            ),
        ),
    ]
