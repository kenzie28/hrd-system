"""Canonical, closed-day attendance materialization and monthly aggregation."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from cuti.models import Cuti, StatusPermohonanCuti, TipeCuti
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from shift.models import HariKerja, Shift

from .models import (
    Absensi,
    CatatanRekapAbsensi,
    Kehadiran,
    RekapAbsensi,
    StatusKehadiran,
)

WEEKDAY_TO_HARI = {
    0: HariKerja.SENIN,
    1: HariKerja.SELASA,
    2: HariKerja.RABU,
    3: HariKerja.KAMIS,
    4: HariKerja.JUMAT,
    5: HariKerja.SABTU,
    6: HariKerja.MINGGU,
}

FULL_DAY_LEAVE = {
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

NO_LOKASI_NOTE = (
    'Karyawan tidak punya lokasi kerja, sehingga jadwal shift tidak bisa ditentukan.'
)


@dataclass(frozen=True)
class DayEvaluation:
    values: dict | None
    notes: tuple[str, ...] = ()


def month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def month_bounds(month: date) -> tuple[date, date]:
    last = calendar.monthrange(month.year, month.month)[1]
    return month, date(month.year, month.month, last)


def iter_days(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def closed_through(month: date, today: date | None = None) -> date | None:
    today = today or timezone.localdate()
    start, end = month_bounds(month)
    cutoff = min(end, today - timedelta(days=1))
    return cutoff if cutoff >= start else None


def shift_window(day: date, shift: Shift) -> tuple[datetime, datetime]:
    start = datetime.combine(day, shift.jam_masuk)
    end = datetime.combine(day, shift.jam_keluar)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def punch_window(punch: Absensi) -> tuple[datetime, datetime]:
    start = datetime.combine(punch.tanggal, punch.jam_masuk)
    return start, start + punch.durasi


def whole_minutes(delta: timedelta) -> int:
    return int(delta.total_seconds() // 60)


def best_match(day: date, shifts: list[Shift], punches: list[Absensi]):
    """Choose closest shift start, then greatest overlap, then stable ids."""
    best = None
    best_key = None
    for shift in shifts:
        shift_start, shift_end = shift_window(day, shift)
        for punch in punches:
            punch_start, punch_end = punch_window(punch)
            overlap = max(
                0.0,
                (
                    min(punch_end, shift_end) - max(punch_start, shift_start)
                ).total_seconds(),
            )
            key = (
                abs((punch_start - shift_start).total_seconds()),
                -overlap,
                punch.pk,
                shift.pk,
            )
            if best_key is None or key < best_key:
                best_key = key
                best = (
                    shift,
                    punch,
                    shift_start,
                    shift_end,
                    punch_start,
                    punch_end,
                )
    return best


def _fmt_range(shift: Shift) -> str:
    return f'{shift.jam_masuk:%H:%M}–{shift.jam_keluar:%H:%M}'


def evaluate_day(karyawan, day: date, *, today: date | None = None) -> DayEvaluation:
    """Evaluate one closed day. An empty value means no canonical row is owed."""
    today = today or timezone.localdate()
    if day >= today:
        raise ValueError('attendance can only be materialized for a closed day')
    if not karyawan.lokasi_kerja_id:
        return DayEvaluation(None)
    if Liburan.objects.filter(tanggal=day).exists():
        return DayEvaluation(None)

    shifts = list(
        Shift.objects.filter(
            lokasi_kerja_id=karyawan.lokasi_kerja_id,
            hari=WEEKDAY_TO_HARI[day.weekday()],
        )
    )
    if not shifts:
        return DayEvaluation(None)

    cuti_rows = list(
        Cuti.objects.filter(
            tanggal=day,
            permohonan__karyawan_id=karyawan.pk,
            permohonan__status=StatusPermohonanCuti.APPROVED,
        ).select_related('permohonan')
    )
    full_day = next(
        (row for row in cuti_rows if row.permohonan.tipe in FULL_DAY_LEAVE), None
    )
    izin_telat = next(
        (
            row
            for row in cuti_rows
            if row.permohonan.tipe == TipeCuti.IZIN_TELAT
        ),
        None,
    )
    izin_pulang = next(
        (
            row
            for row in cuti_rows
            if row.permohonan.tipe == TipeCuti.IZIN_PULANG_CEPAT
        ),
        None,
    )
    punches = list(
        Absensi.objects.filter(karyawan=karyawan, tanggal=day).select_related('lokasi')
    )
    permohonan = (
        PermohonanLembur.objects.filter(
            karyawan=karyawan,
            tanggal=day,
            status=StatusPermohonanLembur.APPROVED,
        )
        .order_by('pk')
        .first()
    )

    cuti_row = full_day or izin_telat or izin_pulang
    if punches:
        shift, punch, shift_start, shift_end, punch_start, punch_end = best_match(
            day, shifts, punches
        )
        late = whole_minutes(punch_start - shift_start) if punch_start > shift_start else 0
        early = whole_minutes(shift_end - punch_end) if punch_end < shift_end else 0
        extra = whole_minutes(punch_end - shift_end) if punch_end > shift_end else 0
        if izin_telat is not None:
            late = 0
        if izin_pulang is not None:
            early = 0
        notes = []
        if late:
            notes.append(
                f'Telat {late} menit. Jadwal masuk {shift.jam_masuk:%H:%M}, '
                f'absen masuk {punch.jam_masuk:%H:%M}.'
            )
        if early:
            notes.append(
                f'Pulang lebih cepat {early} menit. '
                f'Jadwal keluar {shift.jam_keluar:%H:%M}, '
                f'absen keluar {punch_end:%H:%M}.'
            )
        if len(punches) > 1:
            notes.append(
                f'Dipakai absen masuk {punch.jam_masuk:%H:%M} di lokasi '
                f'{punch.lokasi_id}. {len(punches) - 1} entri lain pada hari ini '
                'tidak dipakai.'
            )
        return DayEvaluation(
            {
                'absensi_id': punch.pk,
                'cuti_id': cuti_row.pk if cuti_row else None,
                'permohonan_lembur_id': permohonan.pk if permohonan else None,
                'shift_id': shift.pk,
                'menit_telat': late,
                'cepat_keluar': early,
                'lembur': extra if permohonan else 0,
                'status': StatusKehadiran.HADIR,
            },
            tuple(notes),
        )

    if full_day is not None:
        shift = min(shifts, key=lambda item: (item.jam_masuk, item.pk))
        return DayEvaluation(
            {
                'absensi_id': None,
                'cuti_id': full_day.pk,
                'permohonan_lembur_id': None,
                'shift_id': shift.pk,
                'menit_telat': 0,
                'cepat_keluar': 0,
                'lembur': 0,
                'status': StatusKehadiran.CUTI,
            }
        )

    ranges = ', '.join(_fmt_range(shift) for shift in sorted(
        shifts, key=lambda item: (item.jam_masuk, item.pk)
    ))
    return DayEvaluation(
        {
            'absensi_id': None,
            'cuti_id': None,
            'permohonan_lembur_id': None,
            'shift_id': None,
            'menit_telat': 0,
            'cepat_keluar': 0,
            'lembur': 0,
            'status': StatusKehadiran.ALPA,
        },
        (f'Tidak hadir (alpa). Jadwal shift {ranges}.',),
    )


def materialize_day(karyawan, day: date, *, today: date | None = None):
    """Create/update/delete canonical Kehadiran and return outcome + evaluation."""
    evaluation = evaluate_day(karyawan, day, today=today)
    existing = Kehadiran.objects.filter(karyawan=karyawan, tanggal=day).first()
    if evaluation.values is None:
        if existing is not None:
            existing.delete()
            return 'deleted', evaluation
        return 'same', evaluation
    if existing is None:
        Kehadiran.objects.create(
            karyawan=karyawan, tanggal=day, **evaluation.values
        )
        return 'created', evaluation
    changed = []
    for field, value in evaluation.values.items():
        if getattr(existing, field) != value:
            setattr(existing, field, value)
            changed.append(field)
    if changed:
        existing.save(update_fields=changed)
        return 'updated', evaluation
    return 'same', evaluation


@transaction.atomic
def aggregate_month(
    karyawan,
    month: date,
    *,
    today: date | None = None,
    notes_by_day: dict[date, tuple[str, ...]] | None = None,
    replace_all_notes: bool = False,
) -> RekapAbsensi:
    """Aggregate canonical rows and replace only requested daily notes."""
    if month.day != 1:
        raise ValueError('month must be the first day of the month')
    cutoff = closed_through(month, today)
    rows = Kehadiran.objects.filter(karyawan=karyawan, tanggal__gte=month)
    if cutoff is None:
        rows = rows.none()
    else:
        rows = rows.filter(tanggal__lte=cutoff)
    sums = rows.aggregate(
        total_menit_telat=Sum('menit_telat'),
        total_menit_lembur=Sum('lembur'),
    )
    counts = {
        'hari_hadir': rows.filter(status=StatusKehadiran.HADIR).count(),
        'hari_telat': rows.filter(menit_telat__gt=0).count(),
        'hari_alpa': rows.filter(status=StatusKehadiran.ALPA).count(),
        'hari_keluar_cepat': rows.filter(cepat_keluar__gt=0).count(),
        'total_menit_telat': sums['total_menit_telat'] or 0,
        'total_menit_lembur': sums['total_menit_lembur'] or 0,
        'materialized_through': cutoff,
    }
    rekap, _ = RekapAbsensi.objects.update_or_create(
        karyawan=karyawan, month=month, defaults=counts
    )

    if replace_all_notes:
        rekap.catatan.filter(tanggal__isnull=False).delete()
    if notes_by_day:
        dates = list(notes_by_day)
        rekap.catatan.filter(tanggal__in=dates).delete()
        CatatanRekapAbsensi.objects.bulk_create(
            [
                CatatanRekapAbsensi(rekap=rekap, tanggal=day, pesan=message)
                for day, messages in notes_by_day.items()
                for message in messages
            ]
        )

    rekap.catatan.filter(tanggal__isnull=True).delete()
    if not karyawan.lokasi_kerja_id:
        CatatanRekapAbsensi.objects.create(rekap=rekap, pesan=NO_LOKASI_NOTE)
    return rekap
