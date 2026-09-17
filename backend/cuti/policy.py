"""Centralized leave (cuti) approval policy.

Defines which employee *levels* a requester of a given level may pick as their
supervisor/approver. Edit ``LEVEL_APPROVER_MAP`` to change the hierarchy.

Rules:
    - Level 1-4 may request anyone from level 5-7.
    - Level 5-6 may request level 7.
    - Level 7 may request level 8.

Cuti Tahunan duration rules (enforced on create):
    - At most 5 consecutive calendar days per request.
    - 4 or 5 consecutive days require at least 28 days' notice.
"""
from datetime import date, timedelta

from django.utils import timezone

from .models import StatusPermohonanCuti

MAX_CONSECUTIVE_TAHUNAN_DAYS = 5
TAHUNAN_ADVANCE_NOTICE_DAYS = 28
TAHUNAN_ADVANCE_NOTICE_MIN_DAYS = 4

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


def tahunan_range_errors(tanggal_mulai, tanggal_selesai, today=None):
    """Field errors for a Cuti Tahunan date range, or an empty dict if valid."""
    today = today or timezone.localdate()
    jumlah_hari = (tanggal_selesai - tanggal_mulai).days + 1
    if jumlah_hari > MAX_CONSECUTIVE_TAHUNAN_DAYS:
        return {
            'tanggal_selesai': (
                f'Cuti tahunan maksimal {MAX_CONSECUTIVE_TAHUNAN_DAYS} hari '
                'berturut-turut.'
            )
        }
    if jumlah_hari >= TAHUNAN_ADVANCE_NOTICE_MIN_DAYS:
        earliest = today + timedelta(days=TAHUNAN_ADVANCE_NOTICE_DAYS)
        if tanggal_mulai < earliest:
            return {
                'tanggal_mulai': (
                    'Pengajuan cuti tahunan 4 atau 5 hari harus dilakukan '
                    f'minimal {TAHUNAN_ADVANCE_NOTICE_DAYS} hari sebelumnya.'
                )
            }
    return {}


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
