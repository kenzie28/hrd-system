from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuti', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permohonancuti',
            name='status',
            field=models.CharField(
                choices=[
                    ('MENUNGGU_SUPERVISOR', 'Menunggu Izin Supervisor'),
                    ('MENUNGGU_HRD', 'Menunggu Izin HRD'),
                    ('DITOLAK', 'Request Ditolak'),
                    ('DIBATALKAN', 'Dibatalkan'),
                    ('APPROVED', 'Approved'),
                    (
                        'MENUNGGU_PEMBATALAN_SUPERVISOR',
                        'Menunggu Pembatalan Supervisor',
                    ),
                    ('MENUNGGU_PEMBATALAN_HRD', 'Menunggu Pembatalan HRD'),
                ],
                default='MENUNGGU_SUPERVISOR',
                max_length=32,
            ),
        ),
    ]
