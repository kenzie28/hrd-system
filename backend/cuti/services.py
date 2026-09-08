"""Workflow helpers for the leave (cuti) request lifecycle."""
from datetime import timedelta

from django.db import transaction

from .models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti


@transaction.atomic
def approve_by_hrd(permohonan: PermohonanCuti, hrd_approver) -> int:
    """Finalize a request that HRD approved and materialize the per-day Cuti rows.

    Returns the number of Cuti (day) rows created. Idempotent per request: any
    existing day rows for the request are cleared first.
    """
    was_approved_before = permohonan.status == StatusPermohonanCuti.APPROVED

    permohonan.status = StatusPermohonanCuti.APPROVED
    permohonan.hrd_approver = hrd_approver
    permohonan.save(update_fields=['status', 'hrd_approver'])

    permohonan.hari_cuti.all().delete()

    rows = []
    current = permohonan.tanggal_mulai
    while current <= permohonan.tanggal_selesai:
        rows.append(Cuti(permohonan=permohonan, tanggal=current))
        current += timedelta(days=1)

    Cuti.objects.bulk_create(rows)

    if permohonan.tipe == TipeCuti.TAHUNAN and not was_approved_before:
        karyawan = permohonan.karyawan
        karyawan.cuti_tahunan = max(0, karyawan.cuti_tahunan - len(rows))
        karyawan.save(update_fields=['cuti_tahunan'])

    return len(rows)


def _jumlah_hari(permohonan: PermohonanCuti) -> int:
    return (permohonan.tanggal_selesai - permohonan.tanggal_mulai).days + 1


@transaction.atomic
def approve_cancellation_by_hrd(permohonan: PermohonanCuti) -> int:
    """Finalize post-approval cancellation: drop day rows and restore quota.

    Returns the number of Cuti (day) rows removed. ``cuti_tahunan`` is restored
    only for Cuti Tahunan, using the day-row count (falling back to the
    inclusive date range if rows were already gone).
    """
    day_count = permohonan.hari_cuti.count()
    if day_count == 0:
        day_count = _jumlah_hari(permohonan)

    permohonan.hari_cuti.all().delete()

    if permohonan.tipe == TipeCuti.TAHUNAN:
        karyawan = permohonan.karyawan
        karyawan.cuti_tahunan += day_count
        karyawan.save(update_fields=['cuti_tahunan'])

    permohonan.status = StatusPermohonanCuti.DIBATALKAN
    permohonan.save(update_fields=['status'])

    return day_count
