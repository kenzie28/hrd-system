"""Turn past punches, full-day leave, and missed shifts into Kehadiran rows.

Dates before today (Asia/Jakarta, or the ``today`` argument) are eligible.
Each unprocessed punch becomes one Hadir row matched to the closest
home-location shift. A scheduled day with no punch becomes Cuti or Alpa.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Min, Q
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
    _iter_days,
    _overlap_seconds,
    _punch_window,
    _shift_window,
    _whole_minutes,
    proses_absensi_bulan,
)


def _closest_shift(day: date, shifts: list[Shift], punch: Absensi) -> Shift:
    punch_start, punch_end = _punch_window(punch)
    best = shifts[0]
    best_key = None
    for shift in shifts:
        shift_start, shift_end = _shift_window(day, shift)
        delta = abs((punch_start - shift_start).total_seconds())
        overlap = _overlap_seconds(punch_start, punch_end, shift_start, shift_end)
        key = (delta, -overlap, shift.pk)
        if best_key is None or key < best_key:
            best_key = key
            best = shift
    return best


def _earliest_shift(shifts: list[Shift]) -> Shift:
    return min(shifts, key=lambda shift: (shift.jam_masuk, shift.pk))


def _minutes(day: date, shift: Shift, punch: Absensi) -> tuple[int, int, int]:
    """Return (minutes late, minutes left early, minutes after shift end)."""
    shift_start, shift_end = _shift_window(day, shift)
    punch_start, punch_end = _punch_window(punch)
    late = _whole_minutes(punch_start - shift_start) if punch_start > shift_start else 0
    early = _whole_minutes(shift_end - punch_end) if punch_end < shift_end else 0
    extra = _whole_minutes(punch_end - shift_end) if punch_end > shift_end else 0
    return late, early, extra


def _delete_placeholders(pairs: set[tuple[str, date]]) -> None:
    items = list(pairs)
    for start in range(0, len(items), 200):
        query = Q()
        for karyawan_id, tanggal in items[start:start + 200]:
            query |= Q(karyawan_id=karyawan_id, tanggal=tanggal)
        Kehadiran.objects.filter(query, absensi__isnull=True).delete()


def _month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def _previous_month_start(today: date) -> date:
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return date(year, month, 1)


@transaction.atomic
def proses_kehadiran(today: date | None = None) -> dict[str, int]:
    """Create missing Kehadiran rows for every date before ``today``.

    Returns how many Hadir, Cuti, and Alpa rows were created. Months that
    gained rows have their RekapAbsensi rebuilt.
    """
    if today is None:
        today = timezone.localdate()

    counts = {'hadir': 0, 'cuti': 0, 'alpa': 0}
    karyawan_list = list(Karyawan.objects.select_related('lokasi_kerja'))
    by_id = {karyawan.karyawan_id: karyawan for karyawan in karyawan_list}
    lokasi_ids = {k.lokasi_kerja_id for k in karyawan_list if k.lokasi_kerja_id}

    shift_map: dict[tuple[str, str], list[Shift]] = defaultdict(list)
    if lokasi_ids:
        for shift in Shift.objects.filter(lokasi_kerja_id__in=lokasi_ids):
            shift_map[(shift.lokasi_kerja_id, shift.hari)].append(shift)

    liburan = set(
        Liburan.objects.filter(tanggal__lt=today).values_list('tanggal', flat=True)
    )

    full_day: dict[tuple[str, date], Cuti] = {}
    izin_telat: dict[tuple[str, date], Cuti] = {}
    izin_pulang: dict[tuple[str, date], Cuti] = {}
    cuti_rows = Cuti.objects.filter(
        tanggal__lt=today,
        permohonan__status=StatusPermohonanCuti.APPROVED,
    ).select_related('permohonan')
    for row in cuti_rows:
        key = (row.permohonan.karyawan_id, row.tanggal)
        if row.permohonan.tipe in _FULL_DAY_LEAVE:
            full_day[key] = row
        elif row.permohonan.tipe == TipeCuti.IZIN_TELAT:
            izin_telat[key] = row
        elif row.permohonan.tipe == TipeCuti.IZIN_PULANG_CEPAT:
            izin_pulang[key] = row

    lembur_map: dict[tuple[str, date], PermohonanLembur] = {}
    for permohonan in PermohonanLembur.objects.filter(
        tanggal__lt=today,
        status=StatusPermohonanLembur.APPROVED,
    ):
        lembur_map[(permohonan.karyawan_id, permohonan.tanggal)] = permohonan

    unprocessed = Absensi.objects.filter(
        tanggal__lt=today,
        kehadiran__isnull=True,
    ).select_related('karyawan')

    hadir_rows: list[Kehadiran] = []
    replaced: set[tuple[str, date]] = set()
    touched: set[date] = set()

    for punch in unprocessed:
        karyawan = by_id.get(punch.karyawan_id)
        if karyawan is None or not karyawan.lokasi_kerja_id:
            continue
        hari = _WEEKDAY_TO_HARI[punch.tanggal.weekday()]
        shifts = shift_map.get((karyawan.lokasi_kerja_id, hari))
        if not shifts:
            continue
        shift = _closest_shift(punch.tanggal, shifts, punch)
        late, early, extra = _minutes(punch.tanggal, shift, punch)
        key = (punch.karyawan_id, punch.tanggal)
        cuti_row = None
        if key in izin_telat:
            late = 0
            cuti_row = izin_telat[key]
        if key in izin_pulang:
            early = 0
            if cuti_row is None:
                cuti_row = izin_pulang[key]
        if cuti_row is None and key in full_day:
            cuti_row = full_day[key]
        permohonan = lembur_map.get(key)
        hadir_rows.append(
            Kehadiran(
                karyawan=karyawan,
                tanggal=punch.tanggal,
                absensi=punch,
                cuti=cuti_row,
                permohonan_lembur=permohonan,
                shift=shift,
                menit_telat=late,
                cepat_keluar=early,
                lembur=extra if permohonan is not None else 0,
                status=StatusKehadiran.HADIR,
            )
        )
        replaced.add(key)
        touched.add(punch.tanggal)

    _delete_placeholders(replaced)
    if hadir_rows:
        Kehadiran.objects.bulk_create(hadir_rows)
    counts['hadir'] = len(hadir_rows)

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
    # Cover the previous calendar month through yesterday, and any older
    # punches or full-day leave so gaps in that backlog are still marked.
    start = _previous_month_start(today)
    if earliest is not None and earliest < start:
        start = earliest
    yesterday = today - timedelta(days=1)
    if start > yesterday:
        _rebuild_rekap(touched)
        return counts

    punch_days = set(
        Absensi.objects.filter(tanggal__gte=start, tanggal__lt=today).values_list(
            'karyawan_id', 'tanggal'
        )
    )
    placeholders = {
        (karyawan_id, tanggal): status
        for karyawan_id, tanggal, status in Kehadiran.objects.filter(
            tanggal__gte=start,
            tanggal__lt=today,
            absensi__isnull=True,
        ).values_list('karyawan_id', 'tanggal', 'status')
    }

    cuti_created: list[Kehadiran] = []
    alpa_created: list[Kehadiran] = []
    replace_with_cuti: set[tuple[str, date]] = set()

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
            if key in punch_days:
                continue
            existing = placeholders.get(key)
            if key in full_day:
                if existing == StatusKehadiran.CUTI:
                    continue
                if existing == StatusKehadiran.ALPA:
                    replace_with_cuti.add(key)
                cuti_created.append(
                    Kehadiran(
                        karyawan=karyawan,
                        tanggal=day,
                        cuti=full_day[key],
                        shift=_earliest_shift(shifts),
                        status=StatusKehadiran.CUTI,
                    )
                )
                touched.add(day)
                continue
            if existing is not None:
                continue
            alpa_created.append(
                Kehadiran(
                    karyawan=karyawan,
                    tanggal=day,
                    shift=_earliest_shift(shifts),
                    status=StatusKehadiran.ALPA,
                )
            )
            touched.add(day)

    _delete_placeholders(replace_with_cuti)
    if cuti_created:
        Kehadiran.objects.bulk_create(cuti_created)
    if alpa_created:
        Kehadiran.objects.bulk_create(alpa_created)
    counts['cuti'] = len(cuti_created)
    counts['alpa'] = len(alpa_created)

    _rebuild_rekap(touched)
    return counts


def _rebuild_rekap(touched: set[date]) -> None:
    for month in sorted({_month_start(day) for day in touched}):
        proses_absensi_bulan(month)
