from django.db import migrations


def copy_approved_dinas(apps, schema_editor):
    """Move approved lembur rows marked DINAS onto the dinas table.

    Stored attendance minutes that came from those rows are cleared. Every
    DINAS lembur row is then deleted, including ones that were never approved.
    """
    PermohonanLembur = apps.get_model('lembur', 'PermohonanLembur')
    Dinas = apps.get_model('dinas', 'Dinas')
    Kehadiran = apps.get_model('absensi', 'Kehadiran')

    Kehadiran.objects.filter(permohonan_lembur__tipe='DINAS').update(
        lembur=0,
        permohonan_lembur_id=None,
    )

    seen = set()
    to_create = []
    rows = (
        PermohonanLembur.objects.filter(tipe='DINAS', status='APPROVED')
        .order_by('id')
        .values_list('karyawan_id', 'tanggal')
    )
    for karyawan_id, tanggal in rows:
        key = (karyawan_id, tanggal)
        if key in seen:
            continue
        seen.add(key)
        to_create.append(Dinas(karyawan_id=karyawan_id, tanggal=tanggal))
    Dinas.objects.bulk_create(to_create)
    PermohonanLembur.objects.filter(tipe='DINAS').delete()


def move_dinas_back_to_lembur(apps, schema_editor):
    PermohonanLembur = apps.get_model('lembur', 'PermohonanLembur')
    Dinas = apps.get_model('dinas', 'Dinas')
    rows = [
        PermohonanLembur(
            karyawan_id=row.karyawan_id,
            tanggal=row.tanggal,
            alasan='',
            tipe='DINAS',
            status='APPROVED',
        )
        for row in Dinas.objects.all().order_by('id')
    ]
    PermohonanLembur.objects.bulk_create(rows)
    Dinas.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dinas', '0001_initial'),
        ('lembur', '0002_permohonanlembur_tipe'),
        ('absensi', '0004_kehadiran'),
    ]

    operations = [
        migrations.RunPython(copy_approved_dinas, move_dinas_back_to_lembur),
    ]
