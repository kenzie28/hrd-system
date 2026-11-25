from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lembur', '0002_permohonanlembur_tipe'),
        ('dinas', '0002_copy_dinas_from_lembur'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='permohonanlembur',
            name='tipe',
        ),
    ]
