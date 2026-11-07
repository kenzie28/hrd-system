import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('karyawan', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TunjanganObat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nominal', models.PositiveBigIntegerField()),
                ('bulan', models.DateField(help_text='First day of the month this allowance applies to.')),
                ('karyawan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tunjangan_obat', to='karyawan.karyawan')),
            ],
            options={
                'verbose_name': 'Tunjangan Obat',
                'verbose_name_plural': 'Tunjangan Obat',
                'ordering': ['-bulan', 'karyawan__nama', 'id'],
            },
        ),
    ]
