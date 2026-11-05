from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lembur', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='permohonanlembur',
            name='tipe',
            field=models.CharField(
                choices=[('BIASA', 'Biasa'), ('DINAS', 'Dinas')],
                default='BIASA',
                max_length=32,
            ),
        ),
    ]
