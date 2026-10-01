from django.db import migrations, models


def dedupe_kehadiran(apps, schema_editor):
    """Keep one row per employee-day before the unique constraint is enforced."""
    Kehadiran = apps.get_model('absensi', 'Kehadiran')
    grouped = {}
    for row in Kehadiran.objects.all().order_by('id'):
        grouped.setdefault((row.karyawan_id, row.tanggal), []).append(row)
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        keeper = next((row for row in rows if row.absensi_id), rows[0])
        for row in rows:
            if row.pk != keeper.pk:
                row.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('absensi', '0004_kehadiran'),
    ]

    operations = [
        migrations.RunPython(dedupe_kehadiran, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='kehadiran',
            name='kehadiran_one_placeholder_per_day',
        ),
        migrations.AddConstraint(
            model_name='kehadiran',
            constraint=models.UniqueConstraint(
                fields=('karyawan', 'tanggal'),
                name='kehadiran_unique_karyawan_tanggal',
            ),
        ),
    ]
