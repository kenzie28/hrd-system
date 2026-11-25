from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0012_karyawan_no_bpjs_rename_kpj'),
    ]

    operations = [
        migrations.AddField(
            model_name='karyawan',
            name='absensi_dihitung',
            field=models.BooleanField(default=True),
        ),
    ]
