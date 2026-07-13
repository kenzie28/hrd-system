"""
TEMPORARY helper used only while testing the Gaji CSV import end-to-end.

Upserts NAMA KARYAWAN / JABATAN / Lokasi Kerja / Wilayah / level (from Gol)
from the gaji CSV onto ``core.Karyawan``, creating the Karyawan (with
``level=1`` when Gol has no usable digit) and/or the ``core.Lokasi`` if they
don't exist yet.

Delete this file and its one call site in ``gaji/services.py``
(``upsert_karyawan_from_gaji_row``) once every Karyawan is properly onboarded
through the normal admin flow and this upsert-on-import behavior is no
longer needed.
"""
from __future__ import annotations

from core.models import Karyawan, Lokasi


def upsert_karyawan_from_gaji_row(
    *,
    karyawan_id: str,
    nama: str,
    jabatan: str,
    lokasi_id: str,
    wilayah: str,
    level: int | None = None,
) -> tuple[Karyawan, bool]:
    """Get-or-create the Karyawan for ``karyawan_id``, syncing basic fields
    from the CSV row. Returns ``(karyawan, created)``.

    ``level`` comes from the first digit in the Gol column (1–8). When omitted
    or invalid, new karyawan default to level 1 and existing levels are left
    unchanged.
    """
    lokasi = None
    if lokasi_id:
        lokasi, _ = Lokasi.objects.get_or_create(
            id=lokasi_id, defaults={'nama': lokasi_id}
        )

    default_level = level if level is not None else 1
    karyawan, created = Karyawan.objects.get_or_create(
        karyawan_id=karyawan_id,
        defaults={
            'nama': nama,
            'jabatan': jabatan,
            'lokasi_kerja': lokasi,
            'wilayah': wilayah,
            'level': default_level,
        },
    )
    if not created:
        karyawan.nama = nama
        karyawan.jabatan = jabatan
        karyawan.lokasi_kerja = lokasi or karyawan.lokasi_kerja
        karyawan.wilayah = wilayah or karyawan.wilayah
        update_fields = ['nama', 'jabatan', 'lokasi_kerja', 'wilayah']
        if level is not None:
            karyawan.level = level
            update_fields.append('level')
        karyawan.save(update_fields=update_fields)

    return karyawan, created
