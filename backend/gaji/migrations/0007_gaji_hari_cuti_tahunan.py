from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gaji', '0006_gaji_tambahan_bca_transfer'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gaji',
            old_name='hari_cuti',
            new_name='hari_cuti_tahunan',
        ),
    ]
