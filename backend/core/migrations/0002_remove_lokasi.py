# Generated manually: drop Lokasi from core state (table kept as core_lokasi).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('karyawan', '0003_alter_karyawan_lokasi_kerja'),
        ('shift', '0002_alter_shift_lokasi_kerja'),
        ('absensi', '0002_alter_absensi_lokasi'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='Lokasi',
                ),
            ],
            database_operations=[],
        ),
    ]
