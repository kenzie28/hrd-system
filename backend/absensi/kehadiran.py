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
    """Ensure one Kehadiran per employee per shift-day before ``today``.

    Returns how many Hadir, Cuti, and Alpa rows were created. Months that
    changed have their RekapAbsensi rebuilt.
    """
    if today is None:
        today = timezone.localdate()

    counts = {'hadir': 0, 'cuti': 0, 'alpa': 0}
    karyawan_list = list(Karyawan.objects.select_related('lokasi_kerja'))
    lokasi_ids = {k.lokasi_kerja_id for k in karyawan_list if k.lokasi_kerja_id}

    shift_map: dict[tuple[str, str], list[Shift]] = defaultdict(list)
    if lokasi_ids:
        for shift in Shift.objects.filter(lokasi_kerja_id__in=lokasi_ids):
            shift_map[(shift.lokasi_kerja_id, shift.hari)].append(shift)

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

    liburan = set(
        Liburan.objects.filter(tanggal__gte=start, tanggal__lt=today).values_list(
            'tanggal', flat=True
        )
    )

    full_day: dict[tuple[str, date], Cuti] = {}
    izin_telat: dict[tuple[str, date], Cuti] = {}
    izin_pulang: dict[tuple[str, date], Cuti] = {}
    for row in Cuti.objects.filter(
        tanggal__gte=start,
        tanggal__lt=today,
        permohonan__status=StatusPermohonanCuti.APPROVED,
    ).select_related('permohonan'):
        key = (row.permohonan.karyawan_id, row.tanggal)
        if row.permohonan.tipe in _FULL_DAY_LEAVE:
            full_day[key] = row
        elif row.permohonan.tipe == TipeCuti.IZIN_TELAT:
            izin_telat[key] = row
        elif row.permohonan.tipe == TipeCuti.IZIN_PULANG_CEPAT:
            izin_pulang[key] = row

    lembur_map: dict[tuple[str, date], PermohonanLembur] = {}
    for permohonan in PermohonanLembur.objects.filter(
        tanggal__gte=start,
        tanggal__lt=today,
        status=StatusPermohonanLembur.APPROVED,
    ):
        lembur_map[(permohonan.karyawan_id, permohonan.tanggal)] = permohonan

    punch_map: dict[tuple[str, date], list[Absensi]] = defaultdict(list)
    for punch in Absensi.objects.filter(tanggal__gte=start, tanggal__lt=today):
        punch_map[(punch.karyawan_id, punch.tanggal)].append(punch)

    existing_map = {
        (row.karyawan_id, row.tanggal): row
        for row in Kehadiran.objects.filter(tanggal__gte=start, tanggal__lt=today)
    }

    touched: set[date] = set()
    for karyawan in karyawan_list:
        if not karyawan.lokasi_kerja_id:
            continue
        for day in _iter_days(start, yesterday):
            if day in liburan:
                continue
            hari = _WEEKDAY_TO_HARI[day.weekday()]
            shifts = shift_map.get((karyawan.lokasi_kerja_id, hari))
            if not shifts:
                continue
            key = (karyawan.karyawan_id, day)
            desired = _compose_day(
                day,
                shifts,
                punch_map.get(key, []),
                full_day=full_day.get(key),
                izin_telat=izin_telat.get(key),
                izin_pulang=izin_pulang.get(key),
                permohonan=lembur_map.get(key),
            )
            outcome = _store_day(existing_map.get(key), karyawan, day, desired)
            if outcome == 'created':
                counts[_status_key(desired['status'])] += 1
                touched.add(day)
            elif outcome == 'updated':
                touched.add(day)

    _rebuild_rekap(touched)
    return counts


def _rebuild_rekap(touched: set[date]) -> None:
    for month in sorted({_month_start(day) for day in touched}):
        proses_absensi_bulan(month)
