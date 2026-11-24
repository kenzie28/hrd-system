from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0004_karyawan_lembur_dibayar'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='status_k_tk',
            field=models.CharField(
                blank=True,
                choices=[
                    ('TK', 'TK'),
                    ('TK1', 'TK1'),
                    ('TK2', 'TK2'),
                    ('TK3', 'TK3'),
                    ('K0', 'K0'),
                    ('K1', 'K1'),
                    ('K2', 'K2'),
                    ('K3', 'K3'),
                ],
                default='',
                max_length=3,
            ),
        ),
    ]
