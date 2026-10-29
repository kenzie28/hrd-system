"""Match a month of punches to each employee's home-location shift.

The obligation comes from ``Karyawan.lokasi_kerja``. A punch at any location
satisfies it. Late, early-leave, and overtime minutes use the home shift, not
the punch location's shift. One appearance is owed per scheduled weekday, even
when that location has several shift rows.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.db import transaction

from cuti.models import Cuti, StatusPermohonanCuti, TipeCuti
from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from shift.models import HariKerja, Shift

from .engine import (
    FULL_DAY_LEAVE,
    WEEKDAY_TO_HARI,
    aggregate_month,
    best_match,
    closed_through,
    iter_days,
    materialize_day,
    whole_minutes,
)
from .models import Absensi, CatatanRekapAbsensi, RekapAbsensi

_WEEKDAY_TO_HARI = {
    0: HariKerja.SENIN,
    1: HariKerja.SELASA,
    2: HariKerja.RABU,
    3: HariKerja.KAMIS,
    4: HariKerja.JUMAT,
    5: HariKerja.SABTU,
    6: HariKerja.MINGGU,
}

# These approved leave types remove the day's obligation entirely.
_FULL_DAY_LEAVE = {
    TipeCuti.IZIN_OFF,
    TipeCuti.TAHUNAN,
    TipeCuti.SAKIT,
    TipeCuti.DUKA_CITA,
    TipeCuti.MELAHIRKAN,
    TipeCuti.ISTRI_MELAHIRKAN,
    TipeCuti.MENIKAH,
    TipeCuti.ANAK_MENIKAH,
    TipeCuti.KHITANAN_ANAK,
    TipeCuti.PEMBAPTISAN_ANAK,
}

_NO_LOKASI = (
    'Karyawan tidak punya lokasi kerja, sehingga jadwal shift tidak bisa ditentukan.'
)


def _month_bounds(month_start: date) -> tuple[date, date]:
    last = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start, date(month_start.year, month_start.month, last)


def _iter_days(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _shift_window(day: date, shift: Shift) -> tuple[datetime, datetime]:
    start = datetime.combine(day, shift.jam_masuk)
    end = datetime.combine(day, shift.jam_keluar)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _punch_window(punch: Absensi) -> tuple[datetime, datetime]:
    start = datetime.combine(punch.tanggal, punch.jam_masuk)
    return start, start + punch.durasi


def _overlap_seconds(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> float:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    return max(0.0, (end - start).total_seconds())


def _whole_minutes(delta: timedelta) -> int:
    return int(delta.total_seconds() // 60)


def _fmt_range(shift: Shift) -> str:
    return f'{shift.jam_masuk:%H:%M}–{shift.jam_keluar:%H:%M}'


def _best_match(day: date, shifts: list[Shift], punches: list[Absensi]):
    """Closest shift start, then greatest overlap, then stable ids."""
    best = None
    best_key = None
    for shift in shifts:
        shift_start, shift_end = _shift_window(day, shift)
        for punch in punches:
            punch_start, punch_end = _punch_window(punch)
            delta = abs((punch_start - shift_start).total_seconds())
            overlap = _overlap_seconds(punch_start, punch_end, shift_start, shift_end)
            key = (delta, -overlap, punch.pk, shift.pk)
            if best_key is None or key < best_key:
                best_key = key
                best = (shift, punch, shift_start, shift_end, punch_start, punch_end)
    return best


def _day_notes(
    day: date,
    shifts: list[Shift],
    punches: list[Absensi],
    *,
    izin_telat: bool,
    izin_pulang_cepat: bool,
    lembur_approved: bool,
) -> tuple[dict, list[tuple[date, str]]]:
    """Return counter increments and dated notes for one scheduled day."""
    counts = {
        'hari_hadir': 0,
        'hari_telat': 0,
        'hari_alpa': 0,
        'hari_keluar_cepat': 0,
        'total_menit_telat': 0,
        'total_menit_lembur': 0,
    }
    notes: list[tuple[date, str]] = []

    if not punches:
        counts['hari_alpa'] = 1
        ordered = sorted(shifts, key=lambda item: (item.jam_masuk, item.pk))
        ranges = ', '.join(_fmt_range(shift) for shift in ordered)
        notes.append((day, f'Tidak hadir (alpa). Jadwal shift {ranges}.'))
        return counts, notes

    shift, punch, shift_start, shift_end, punch_start, punch_end = _best_match(
        day, shifts, punches
    )
    counts['hari_hadir'] = 1

    if punch_start > shift_start:
        late = _whole_minutes(punch_start - shift_start)
        if late > 0 and not izin_telat:
            counts['hari_telat'] = 1
            counts['total_menit_telat'] = late
            notes.append(
                (
                    day,
                    f'Telat {late} menit. Jadwal masuk {shift.jam_masuk:%H:%M}, '
                    f'absen masuk {punch.jam_masuk:%H:%M}.',
                )
            )

    if punch_end < shift_end:
        early = _whole_minutes(shift_end - punch_end)
        if early > 0 and not izin_pulang_cepat:
            counts['hari_keluar_cepat'] = 1
            notes.append(
                (
                    day,
                    f'Pulang lebih cepat {early} menit. Jadwal keluar {shift.jam_keluar:%H:%M}, '
                    f'absen keluar {punch_end:%H:%M}.',
                )
            )

    if lembur_approved and punch_end > shift_end:
        extra = _whole_minutes(punch_end - shift_end)
        if extra > 0:
            counts['total_menit_lembur'] = extra

    if len(punches) > 1:
        lain = len(punches) - 1
        notes.append(
            (
                day,
                f'Dipakai absen masuk {punch.jam_masuk:%H:%M} di lokasi {punch.lokasi_id}. '
                f'{lain} entri lain pada hari ini tidak dipakai.',
            )
        )

    return counts, notes


@transaction.atomic
def proses_absensi_bulan(
    month_start: date, *, today: date | None = None
) -> list[RekapAbsensi]:
    """Compatibility reconciliation through the last closed date in the month."""
    if month_start.day != 1:
        raise ValueError('month_start must be the first day of the month')

    karyawan_list = list(
        Karyawan.objects.select_related('lokasi_kerja').order_by('nama', 'karyawan_id')
    )
    cutoff = closed_through(month_start, today)
    saved = []
    for karyawan in karyawan_list:
        notes_by_day = {}
        if cutoff is not None:
            for day in iter_days(month_start, cutoff):
                _outcome, evaluation = materialize_day(karyawan, day, today=today)
                notes_by_day[day] = evaluation.notes
        saved.append(
            aggregate_month(
                karyawan,
                month_start,
                today=today,
                notes_by_day=notes_by_day,
                replace_all_notes=True,
            )
        )
    return saved
