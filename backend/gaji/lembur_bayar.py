"""Overtime hours, off-day days, and banked hours for one payroll month.

Pay is applied in ``build_gaji`` only through the existing ``gaji_lembur``
amount. Unpaid hours are added to ``Karyawan.akumulasi_lembur`` by
``write_gaji``, which records the hours on ``Gaji.jam_diakumulasi`` so a
reprocess replaces that month instead of adding it again.

To remove this feature, delete this module, the two call sites in
``services.py``, and the ``jam_diakumulasi`` column. Hours already stored on
``Karyawan.akumulasi_lembur`` stay until subtracted by each row's
``jam_diakumulasi``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from absensi.models import Absensi, Kehadiran
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from shift.models import HariKerja, Shift

UPAH_JAM_LEMBUR_NUMERATOR = 110_000
UPAH_JAM_LEMBUR_DENOMINATOR = 6
UPAH_HARI_LEMBUR = 133_000

_WEEKDAY_TO_HARI = {
    0: HariKerja.SENIN,
    1: HariKerja.SELASA,
    2: HariKerja.RABU,
    3: HariKerja.KAMIS,
    4: HariKerja.JUMAT,
    5: HariKerja.SABTU,
    6: HariKerja.MINGGU,
}


@dataclass(frozen=True)
class LemburHitung:
    jam: int
    hari: int
    gaji: Decimal


def _round_half_up(amount: Decimal) -> int:
    return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _scheduled_weekdays(karyawan) -> set[str]:
    """Weekdays this employee's lokasi is scheduled to work.

    An empty set means no weekday is scheduled, including when the employee
    has no lokasi. An approved request on such a day counts as an off day.
    """
    if not karyawan.lokasi_kerja_id:
        return set()
    return set(
        Shift.objects.filter(lokasi_kerja_id=karyawan.lokasi_kerja_id).values_list(
            'hari', flat=True
        )
    )


def _hari_dates(karyawan, start: date, end: date) -> set[date]:
    """Approved lembur on a liburan or a day with no scheduled shift."""
    holidays = set(
        Liburan.objects.filter(tanggal__gte=start, tanggal__lte=end).values_list(
            'tanggal', flat=True
        )
    )
    scheduled = _scheduled_weekdays(karyawan)
    dates: set[date] = set()
    approved = (
        PermohonanLembur.objects.filter(
            karyawan=karyawan,
            tanggal__gte=start,
            tanggal__lte=end,
            status=StatusPermohonanLembur.APPROVED,
        )
        .values_list('tanggal', flat=True)
        .distinct()
    )
    for tanggal in approved:
        if tanggal in holidays or _WEEKDAY_TO_HARI[tanggal.weekday()] not in scheduled:
            dates.add(tanggal)
    return dates


def _menit(karyawan, start: date, end: date, hari_dates: set[date]) -> int:
    """Workday overtime minutes, plus the full punch on each off-day or liburan."""
    recorded = Kehadiran.objects.filter(
        karyawan=karyawan, tanggal__gte=start, tanggal__lte=end
    )
    if hari_dates:
        recorded = recorded.exclude(tanggal__in=hari_dates)
    menit = recorded.aggregate(total=Sum('lembur'))['total'] or 0

    if not hari_dates:
        return menit
    punched = Absensi.objects.filter(
        karyawan=karyawan, tanggal__in=hari_dates
    ).aggregate(total=Sum('durasi'))['total'] or timedelta(0)
    return menit + int(punched.total_seconds() // 60)


def hitung_lembur(karyawan, start: date, end: date) -> LemburHitung:
    """Hours, off-day count, and the exact ``gaji_lembur`` for this month.

    ``gaji`` is zero when lembur is not paid. The exact amount is what the tax
    base uses; the caller rounds it when storing the component.
    """
    hari_dates = _hari_dates(karyawan, start, end)
    jam = _round_half_up(Decimal(_menit(karyawan, start, end, hari_dates)) / Decimal(60))
    hari = len(hari_dates)
    if karyawan.lembur_dibayar:
        gaji = (
            Decimal(jam) * Decimal(UPAH_JAM_LEMBUR_NUMERATOR)
            / Decimal(UPAH_JAM_LEMBUR_DENOMINATOR)
            + Decimal(hari) * Decimal(UPAH_HARI_LEMBUR)
        )
    else:
        gaji = Decimal(0)
    return LemburHitung(jam=jam, hari=hari, gaji=gaji)
