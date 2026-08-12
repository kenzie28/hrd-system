# Generated manually: retarget FK to lokasi.Lokasi (same physical table).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0002_karyawan_cuti_tahunan'),
        ('lokasi', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='karyawan',
                    name='lokasi_kerja',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='karyawan',
                        to='lokasi.lokasi',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
