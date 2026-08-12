# Generated manually: retarget FK to lokasi.Lokasi (same physical table).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absensi', '0001_initial'),
        ('lokasi', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='absensi',
                    name='lokasi',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='absensi',
                        to='lokasi.lokasi',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
