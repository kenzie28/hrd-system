from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gaji', '0005_gaji_jam_diakumulasi'),
    ]

    operations = [
        migrations.AddField(
            model_name='gaji',
            name='gaji_tambahan',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gaji',
            name='bca_transfer',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
