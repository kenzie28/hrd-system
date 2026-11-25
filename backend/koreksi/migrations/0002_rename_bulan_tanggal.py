from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('koreksi', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='koreksi',
            old_name='bulan',
            new_name='tanggal',
        ),
        migrations.AlterField(
            model_name='koreksi',
            name='tanggal',
            field=models.DateField(),
        ),
        migrations.AlterModelOptions(
            name='koreksi',
            options={
                'ordering': ['-tanggal', 'karyawan__nama', 'id'],
                'verbose_name_plural': 'Koreksi',
            },
        ),
    ]
