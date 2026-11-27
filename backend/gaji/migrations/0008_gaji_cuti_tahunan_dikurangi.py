from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gaji', '0007_gaji_hari_cuti_tahunan'),
    ]

    operations = [
        migrations.AddField(
            model_name='gaji',
            name='cuti_tahunan_dikurangi',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'Annual-leave days this row removed from Karyawan.cuti_tahunan '
                    'because late minutes reached 60. Restored before a reprocess.'
                ),
            ),
        ),
    ]
