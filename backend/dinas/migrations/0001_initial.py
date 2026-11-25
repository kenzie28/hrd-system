import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('karyawan', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dinas',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('tanggal', models.DateField()),
                (
                    'karyawan',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='dinas',
                        to='karyawan.karyawan',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Dinas',
                'verbose_name_plural': 'Dinas',
                'ordering': ['-tanggal', 'karyawan__nama', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='dinas',
            constraint=models.UniqueConstraint(
                fields=('karyawan', 'tanggal'),
                name='dinas_unique_karyawan_tanggal',
            ),
        ),
    ]
