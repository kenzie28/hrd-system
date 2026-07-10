"""Workflow helpers for the leave (cuti) request lifecycle."""
from datetime import timedelta

from django.db import transaction

from .models import Cuti, PermohonanCuti, StatusPermohonanCuti


@transaction.atomic
def approve_by_hrd(permohonan: PermohonanCuti, hrd_approver) -> int:
    """Finalize a request that HRD approved and materialize the per-day Cuti rows.

    Returns the number of Cuti (day) rows created. Idempotent per request: any
    existing day rows for the request are cleared first.
    """
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
    return len(rows)
