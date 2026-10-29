# Generated manually for incremental attendance materialization.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absensi', '0006_kehadiran_shift_nullable'),
        ('karyawan', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rekapabsensi',
            name='materialized_through',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='PendingAttendanceDay',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('tanggal', models.DateField()),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'karyawan',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='+',
                        to='karyawan.karyawan',
                    ),
                ),
            ],
            options={'ordering': ['tanggal', 'karyawan_id']},
        ),
        migrations.CreateModel(
            name='PendingAttendanceMonth',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'month',
                    models.DateField(help_text='First day of the affected month.'),
                ),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'karyawan',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='+',
                        to='karyawan.karyawan',
                    ),
                ),
            ],
            options={'ordering': ['month', 'karyawan_id']},
        ),
        migrations.AddConstraint(
            model_name='pendingattendanceday',
            constraint=models.UniqueConstraint(
                fields=('karyawan', 'tanggal'),
                name='pending_attendance_day_unique_key',
            ),
        ),
        migrations.AddConstraint(
            model_name='pendingattendancemonth',
            constraint=models.UniqueConstraint(
                fields=('karyawan', 'month'),
                name='pending_attendance_month_unique_key',
            ),
        ),
    ]
