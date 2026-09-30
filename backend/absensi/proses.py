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
def proses_absensi_bulan(month_start: date) -> list[RekapAbsensi]:
    """Replace every employee's RekapAbsensi for ``month_start`` (day must be 1)."""
    if month_start.day != 1:
        raise ValueError('month_start must be the first day of the month')

    start, end = _month_bounds(month_start)
    karyawan_list = list(
        Karyawan.objects.select_related('lokasi_kerja').order_by('nama', 'karyawan_id')
    )
    lokasi_ids = {k.lokasi_kerja_id for k in karyawan_list if k.lokasi_kerja_id}

    shift_map: dict[tuple[str, str], list[Shift]] = defaultdict(list)
    if lokasi_ids:
        for shift in Shift.objects.filter(lokasi_kerja_id__in=lokasi_ids):
            shift_map[(shift.lokasi_kerja_id, shift.hari)].append(shift)

    punch_map: dict[tuple[str, date], list[Absensi]] = defaultdict(list)
    for punch in Absensi.objects.filter(tanggal__gte=start, tanggal__lte=end).select_related(
        'lokasi'
    ):
        punch_map[(punch.karyawan_id, punch.tanggal)].append(punch)

    liburan = set(
        Liburan.objects.filter(tanggal__gte=start, tanggal__lte=end).values_list(
            'tanggal', flat=True
        )
    )

    full_day: set[tuple[str, date]] = set()
    izin_telat: set[tuple[str, date]] = set()
    izin_pulang: set[tuple[str, date]] = set()
    cuti_rows = Cuti.objects.filter(
        tanggal__gte=start,
        tanggal__lte=end,
        permohonan__status=StatusPermohonanCuti.APPROVED,
    ).select_related('permohonan')
    for row in cuti_rows:
        key = (row.permohonan.karyawan_id, row.tanggal)
        if row.permohonan.tipe in _FULL_DAY_LEAVE:
            full_day.add(key)
        elif row.permohonan.tipe == TipeCuti.IZIN_TELAT:
            izin_telat.add(key)
        elif row.permohonan.tipe == TipeCuti.IZIN_PULANG_CEPAT:
            izin_pulang.add(key)

    approved_lembur = set(
        PermohonanLembur.objects.filter(
            tanggal__gte=start,
            tanggal__lte=end,
            status=StatusPermohonanLembur.APPROVED,
        ).values_list('karyawan_id', 'tanggal')
    )

    saved_ids: list[int] = []
    for karyawan in karyawan_list:
        counts = {
            'hari_hadir': 0,
            'hari_telat': 0,
            'hari_alpa': 0,
            'hari_keluar_cepat': 0,
            'total_menit_telat': 0,
            'total_menit_lembur': 0,
        }
        notes: list[tuple[date | None, str]] = []

        if not karyawan.lokasi_kerja_id:
            notes.append((None, _NO_LOKASI))
        else:
            for day in _iter_days(start, end):
                if day in liburan:
                    continue
                key = (karyawan.karyawan_id, day)
                if key in full_day:
                    continue
                hari = _WEEKDAY_TO_HARI[day.weekday()]
                shifts = shift_map.get((karyawan.lokasi_kerja_id, hari))
                if not shifts:
                    continue
                day_counts, day_notes = _day_notes(
                    day,
                    shifts,
                    punch_map.get(key, []),
                    izin_telat=key in izin_telat,
                    izin_pulang_cepat=key in izin_pulang,
                    lembur_approved=key in approved_lembur,
                )
                for name, value in day_counts.items():
                    counts[name] += value
                notes.extend(day_notes)

        rekap, _created = RekapAbsensi.objects.update_or_create(
            karyawan=karyawan,
            month=month_start,
            defaults=counts,
        )
        rekap.catatan.all().delete()
        if notes:
            CatatanRekapAbsensi.objects.bulk_create(
                [
                    CatatanRekapAbsensi(rekap=rekap, tanggal=tanggal, pesan=pesan)
                    for tanggal, pesan in notes
                ]
            )
        saved_ids.append(rekap.pk)

    return list(
        RekapAbsensi.objects.filter(pk__in=saved_ids)
        .select_related('karyawan')
        .prefetch_related('catatan')
        .order_by('karyawan__nama', 'karyawan_id')
    )
