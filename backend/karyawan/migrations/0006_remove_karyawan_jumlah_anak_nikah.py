from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('karyawan', '0005_karyawan_status_k_tk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='karyawan',
            name='jumlah_anak',
        ),
        migrations.RemoveField(
            model_name='karyawan',
            name='nikah',
        ),
    ]
