# Generated manually: retarget FK to lokasi.Lokasi (same physical table).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shift', '0001_initial'),
        ('lokasi', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='shift',
                    name='lokasi_kerja',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='shifts',
                        to='lokasi.lokasi',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
