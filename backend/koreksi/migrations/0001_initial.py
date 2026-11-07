import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('karyawan', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Koreksi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipe', models.CharField(choices=[('ADMIN', 'Koreksi Admin'), ('ABSENSI', 'Koreksi Absensi')], max_length=16)),
                ('nominal', models.BigIntegerField()),
                ('bulan', models.DateField(help_text='First day of the month this correction applies to.')),
                ('karyawan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='koreksi', to='karyawan.karyawan')),
            ],
            options={
                'verbose_name_plural': 'Koreksi',
                'ordering': ['-bulan', 'karyawan__nama', 'id'],
            },
        ),
    ]
