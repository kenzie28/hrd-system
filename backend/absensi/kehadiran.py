"""Build one Kehadiran for each past day whose weekday has a home-location shift.

The row is assembled from that shift plus the day's punch and/or approved leave.
A full-day leave has no Absensi. A punch at any location still uses the home shift.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Min
from django.utils import timezone

from cuti.models import Cuti, StatusPermohonanCuti, TipeCuti
from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from shift.models import Shift

from .engine import aggregate_month, iter_days, materialize_day, month_start
from .models import Absensi, Kehadiran, StatusKehadiran
from .proses import (
    _FULL_DAY_LEAVE,
    _WEEKDAY_TO_HARI,
    _best_match,
    _iter_days,
    _whole_minutes,
    proses_absensi_bulan,
)


def _earliest_shift(shifts: list[Shift]) -> Shift:
    return min(shifts, key=lambda shift: (shift.jam_masuk, shift.pk))


def _month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def _previous_month_start(today: date) -> date:
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return date(year, month, 1)


def _status_key(status: str) -> str:
    return {
        StatusKehadiran.HADIR: 'hadir',
        StatusKehadiran.CUTI: 'cuti',
        StatusKehadiran.ALPA: 'alpa',
    }[status]


def _compose_day(
    day: date,
    shifts: list[Shift],
    punches: list[Absensi],
    *,
    full_day: Cuti | None,
    izin_telat: Cuti | None,
    izin_pulang: Cuti | None,
    permohonan: PermohonanLembur | None,
) -> dict:
    """One scheduled day: shift, plus the punch and/or leave that apply."""
    cuti_row = full_day or izin_telat or izin_pulang
    if punches:
        shift, punch, shift_start, shift_end, punch_start, punch_end = _best_match(
            day, shifts, punches
        )
        late = _whole_minutes(punch_start - shift_start) if punch_start > shift_start else 0
        early = _whole_minutes(shift_end - punch_end) if punch_end < shift_end else 0
        extra = _whole_minutes(punch_end - shift_end) if punch_end > shift_end else 0
        if izin_telat is not None:
            late = 0
        if izin_pulang is not None:
            early = 0
        return {
            'absensi_id': punch.pk,
            'cuti_id': cuti_row.pk if cuti_row is not None else None,
            'permohonan_lembur_id': permohonan.pk if permohonan is not None else None,
            'shift_id': shift.pk,
            'menit_telat': late,
            'cepat_keluar': early,
            'lembur': extra if permohonan is not None else 0,
            'status': StatusKehadiran.HADIR,
        }
    if full_day is not None:
        return {
            'absensi_id': None,
            'cuti_id': full_day.pk,
            'permohonan_lembur_id': None,
            'shift_id': _earliest_shift(shifts).pk,
            'menit_telat': 0,
            'cepat_keluar': 0,
            'lembur': 0,
            'status': StatusKehadiran.CUTI,
        }
    # A shift exists for this weekday, but there is no punch: absence, with no
    # shift row attached. Weekdays with no home-location shift are not visited.
    return {
        'absensi_id': None,
        'cuti_id': None,
        'permohonan_lembur_id': None,
        'shift_id': None,
        'menit_telat': 0,
        'cepat_keluar': 0,
        'lembur': 0,
        'status': StatusKehadiran.ALPA,
    }


def _store_day(existing: Kehadiran | None, karyawan, day: date, desired: dict) -> str:
    """Insert or update the day's row. Return ``created``, ``updated``, or ``same``."""
    if existing is None:
        Kehadiran.objects.create(karyawan=karyawan, tanggal=day, **desired)
        return 'created'
    changed = False
    for field, value in desired.items():
        if getattr(existing, field) != value:
            setattr(existing, field, value)
            changed = True
    if changed:
        existing.save()
        return 'updated'
    return 'same'


@transaction.atomic
def proses_kehadiran(today: date | None = None) -> dict[str, int]:
    """Compatibility reconciliation of historical days before ``today``."""
    if today is None:
        today = timezone.localdate()

    counts = {'hadir': 0, 'cuti': 0, 'alpa': 0}
    karyawan_list = list(Karyawan.objects.select_related('lokasi_kerja'))
    earliest_absensi = Absensi.objects.filter(tanggal__lt=today).aggregate(Min('tanggal'))
    earliest_cuti = Cuti.objects.filter(
        tanggal__lt=today,
        permohonan__status=StatusPermohonanCuti.APPROVED,
        permohonan__tipe__in=_FULL_DAY_LEAVE,
    ).aggregate(Min('tanggal'))
    candidates = [
        value
        for value in (earliest_absensi['tanggal__min'], earliest_cuti['tanggal__min'])
        if value is not None
    ]
    earliest = min(candidates) if candidates else None
    start = _previous_month_start(today)
    if earliest is not None and earliest < start:
        start = earliest
    yesterday = today - timedelta(days=1)
    if start > yesterday:
        return counts

    touched: dict[tuple[str, date], dict[date, tuple[str, ...]]] = defaultdict(dict)
    for karyawan in karyawan_list:
        for day in iter_days(start, yesterday):
            outcome, evaluation = materialize_day(karyawan, day, today=today)
            if outcome == 'created':
                counts[_status_key(evaluation.values['status'])] += 1
            if outcome != 'same':
                touched[(karyawan.pk, month_start(day))][day] = evaluation.notes

    by_id = {row.pk: row for row in karyawan_list}
    for (karyawan_id, month), notes in touched.items():
        aggregate_month(
            by_id[karyawan_id], month, today=today, notes_by_day=notes
        )
    return counts


def _rebuild_rekap(touched: set[date]) -> None:
    for month in sorted({_month_start(day) for day in touched}):
        proses_absensi_bulan(month)
