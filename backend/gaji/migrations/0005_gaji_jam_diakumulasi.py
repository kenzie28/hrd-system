from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gaji', '0004_gaji_level_0_to_9'),
    ]

    operations = [
        migrations.AddField(
            model_name='gaji',
            name='jam_diakumulasi',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Hours this row added to Karyawan.akumulasi_lembur. Zero when lembur is paid.',
            ),
        ),
    ]
