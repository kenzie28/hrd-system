"""Centralized leave (cuti) approval policy.

Defines which employee *levels* a requester of a given level may pick as their
supervisor/approver. Edit ``LEVEL_APPROVER_MAP`` to change the hierarchy.

Rules:
    - Level 1-4 may request anyone from level 5-7.
    - Level 5-6 may request level 7.
    - Level 7 may request level 8.
"""
from datetime import date

from django.utils import timezone

from .models import StatusPermohonanCuti

LEVEL_APPROVER_MAP = {
    1: [5, 6, 7],
    2: [5, 6, 7],
    3: [5, 6, 7],
    4: [5, 6, 7],
    5: [6, 7],
    6: [7, 8],
    7: [8],
    8: [8],
}

# Employees at this level (and above) can act as supervisors in the portal
# approval tab.
MIN_SUPERVISOR_LEVEL = 5


def eligible_supervisor_levels(level):
    """Return the list of levels a requester of ``level`` may pick as supervisor."""
    return LEVEL_APPROVER_MAP.get(level, [])


def cancellation_cutoff(today=None):
    """First day of the previous calendar month.

    Approved leave with ``tanggal_mulai`` on or after this date can still be
    cancelled. Example: on 8 Sep 2026 the cutoff is 1 Aug 2026.
    """
    today = today or timezone.localdate()
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def can_request_cancellation(permohonan, today=None):
    """True when the employee may start post-approval Batal Cuti."""
    return (
        permohonan.status == StatusPermohonanCuti.APPROVED
        and permohonan.tanggal_mulai >= cancellation_cutoff(today)
    )
