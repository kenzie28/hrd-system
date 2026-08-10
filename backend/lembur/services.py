"""Workflow helpers for the overtime (lembur) request lifecycle."""
from django.db import transaction

from .models import PermohonanLembur, StatusPermohonanLembur


@transaction.atomic
def approve_by_hrd(permohonan: PermohonanLembur, hrd_approver) -> None:
    """Finalize a request that HRD approved."""
    permohonan.status = StatusPermohonanLembur.APPROVED
    permohonan.hrd_approver = hrd_approver
    permohonan.save(update_fields=['status', 'hrd_approver'])
