"""Build one employee's payroll snapshot for a month."""
from __future__ import annotations

import calendar
import csv
import io
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from absensi.models import Kehadiran, StatusKehadiran
from cuti.models import Cuti, TipeCuti
from karyawan.models import Karyawan
from koreksi.models import Koreksi, TipeKoreksi
from lembur.models import PermohonanLembur, StatusPermohonanLembur, TipeLembur
from obat.models import TunjanganObat

from .models import Gaji
from .ter import ter_fraction

_BPJS_OF_BASE = (
    ('pot_bpjs_jht', Decimal('0.02')),
    ('pot_bpjs_jp', Decimal('0.01')),
    ('pot_bpjs_kesehatan', Decimal('0.01')),
    ('beban_bpjs_kesehatan', Decimal('0.04')),
    ('beban_bpjs_jht', Decimal('0.037')),
    ('beban_bpjs_jp', Decimal('0.02')),
    ('beban_bpjs_jkm', Decimal('0.003')),
    ('beban_bjps_jkk', Decimal('0.0024')),
)


def round_half_up(amount: Decimal) -> int:
    return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def parse_bulan(value) -> date:
    """Accept ``YYYY-MM`` and return the first day of that month."""
    if not isinstance(value, str):
        raise ValueError('bulan harus format YYYY-MM.')
    parts = value.split('-')
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError('bulan harus format YYYY-MM.')
    try:
        year = int(parts[0])
        month = int(parts[1])
        return date(year, month, 1)
    except ValueError as exc:
        raise ValueError('bulan harus format YYYY-MM.') from exc


def month_bounds(periode: date) -> tuple[date, date]:
    start = date(periode.year, periode.month, 1)
    last = calendar.monthrange(start.year, start.month)[1]
    return start, date(start.year, start.month, last)


def _attendance(karyawan: Karyawan, start: date, end: date) -> dict:
    rows = Kehadiran.objects.filter(
        karyawan=karyawan, tanggal__gte=start, tanggal__lte=end
    )
    sums = rows.aggregate(
        total_menit_telat=Sum('menit_telat'),
        total_menit_lembur=Sum('lembur'),
    )
    menit_lembur = sums['total_menit_lembur'] or 0
    return {
        'hari_hadir': rows.filter(status=StatusKehadiran.HADIR).count(),
        'hari_telat': rows.filter(menit_telat__gt=0).count(),
        'total_menit_telat': sums['total_menit_telat'] or 0,
        'hari_alpa': rows.filter(status=StatusKehadiran.ALPA).count(),
        'hari_lembur': rows.filter(lembur__gt=0).count(),
        'jam_lembur': round_half_up(Decimal(menit_lembur) / Decimal(60)),
    }


def _leave_days(karyawan: Karyawan, start: date, end: date) -> dict:
    sakit: set[date] = set()
    cuti: set[date] = set()
    tambahan: set[date] = set()
    off: set[date] = set()
    rows = Cuti.objects.filter(
        permohonan__karyawan=karyawan,
        tanggal__gte=start,
        tanggal__lte=end,
    ).values_list('tanggal', 'permohonan__tipe')
    for tanggal, tipe in rows:
        if tipe == TipeCuti.SAKIT:
            sakit.add(tanggal)
        elif tipe == TipeCuti.TAHUNAN:
            cuti.add(tanggal)
        elif tipe == TipeCuti.IZIN_OFF:
            off.add(tanggal)
        elif tipe.startswith('CUTI_'):
            tambahan.add(tanggal)
    return {
        'hari_sakit': len(sakit),
        'hari_cuti': len(cuti),
        'hari_cuti_tambahan': len(tambahan),
        'hari_off': len(off),
    }


def _hari_dinas(karyawan: Karyawan, start: date, end: date) -> int:
    return (
        PermohonanLembur.objects.filter(
            karyawan=karyawan,
            tipe=TipeLembur.DINAS,
            status=StatusPermohonanLembur.APPROVED,
            tanggal__gte=start,
            tanggal__lte=end,
        )
        .values('tanggal')
        .distinct()
        .count()
    )


def _nominal_sum(queryset) -> int:
    return queryset.aggregate(total=Sum('nominal'))['total'] or 0


def build_gaji(karyawan: Karyawan, periode: date) -> Gaji:
    """Fill a ``Gaji`` row for this employee and month. The caller saves it."""
    start, end = month_bounds(periode)
    gaji = Gaji.objects.filter(karyawan=karyawan, periode=start).first()
    if gaji is None:
        gaji = Gaji(karyawan=karyawan, periode=start)

    gaji.level = karyawan.level
    gaji.jabatan = karyawan.jabatan
    gaji.lembur_dibayar = karyawan.lembur_dibayar
    gaji.status_k_tk = karyawan.status_k_tk
    gaji.base_gaji_bpjs = int(karyawan.base_gaji)
    gaji.gaji_bulanan = int(karyawan.gaji_bulanan)

    for field, value in _attendance(karyawan, start, end).items():
        setattr(gaji, field, value)
    for field, value in _leave_days(karyawan, start, end).items():
        setattr(gaji, field, value)
    gaji.hari_dinas = _hari_dinas(karyawan, start, end)

    gaji.tunjangan_obat = _nominal_sum(
        TunjanganObat.objects.filter(karyawan=karyawan, bulan=start)
    )
    gaji.koreksi_absensi = _nominal_sum(
        Koreksi.objects.filter(
            karyawan=karyawan, bulan=start, tipe=TipeKoreksi.ABSENSI
        )
    )
    gaji.koreksi_admin = _nominal_sum(
        Koreksi.objects.filter(
            karyawan=karyawan, bulan=start, tipe=TipeKoreksi.ADMIN
        )
    )

    base = Decimal(gaji.base_gaji_bpjs)
    for field, rate in _BPJS_OF_BASE:
        setattr(gaji, field, round_half_up(base * rate))

    gaji.pot_alpa = round_half_up(
        Decimal(gaji.hari_alpa) * Decimal(gaji.gaji_bulanan) / Decimal(20)
    )
    gaji.gaji_lembur = 0
    gaji.tunjangan_dinas = 0
    gaji.uang_terima_kasih = 0

    net = gaji.net_penghasilan
    fraction = ter_fraction(gaji.ter_status, net)
    gaji.persentase_pph21 = (fraction * Decimal(100)).quantize(Decimal('0.01'))
    gaji.pot_pph21 = round_half_up(Decimal(net) * fraction)
    gaji.total_gaji = max(0, net - gaji.total_bpjs_benefit - gaji.pot_pph21)
    return gaji


def write_gaji(karyawan: Karyawan, periode: date) -> Gaji:
    gaji = build_gaji(karyawan, periode)
    gaji.save()
    return gaji


GAJI_EXPORT_COLUMNS = (
    'karyawan_id',
    'nama',
    'level',
    'jabatan',
    'periode',
    'hari_hadir',
    'hari_telat',
    'total_menit_telat',
    'hari_sakit',
    'hari_cuti',
    'hari_cuti_tambahan',
    'hari_off',
    'hari_alpa',
    'hari_dinas',
    'base_gaji_bpjs',
    'gaji_bulanan',
    'jam_lembur',
    'hari_lembur',
    'lembur_dibayar',
    'gaji_lembur',
    'tunjangan_obat',
    'tunjangan_dinas',
    'uang_terima_kasih',
    'pot_alpa',
    'koreksi_absensi',
    'koreksi_admin',
    'pot_bpjs_jht',
    'pot_bpjs_jp',
    'pot_bpjs_kesehatan',
    'total_pot_bpjs',
    'beban_bpjs_kesehatan',
    'beban_bpjs_jht',
    'beban_bpjs_jp',
    'beban_bpjs_jkm',
    'beban_bjps_jkk',
    'total_beban_bpjs',
    'total_bpjs_benefit',
    'status_k_tk',
    'ter_status',
    'net_penghasilan',
    'persentase_pph21',
    'pot_pph21',
    'total_gaji',
)


def gaji_for_month(periode: date):
    start, _end = month_bounds(periode)
    return (
        Gaji.objects.filter(periode=start)
        .select_related('karyawan')
        .order_by('karyawan__nama', 'karyawan_id')
    )


def export_gaji_csv(periode: date) -> str:
    """CSV of every payroll row for the month, including calculated totals."""
    start, _end = month_bounds(periode)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(GAJI_EXPORT_COLUMNS)
    for gaji in gaji_for_month(start):
        writer.writerow(
            [
                gaji.karyawan_id,
                gaji.karyawan.nama,
                gaji.level,
                gaji.jabatan,
                f'{gaji.periode:%Y-%m}',
                gaji.hari_hadir,
                gaji.hari_telat,
                gaji.total_menit_telat,
                gaji.hari_sakit,
                gaji.hari_cuti,
                gaji.hari_cuti_tambahan,
                gaji.hari_off,
                gaji.hari_alpa,
                gaji.hari_dinas,
                gaji.base_gaji_bpjs,
                gaji.gaji_bulanan,
                gaji.jam_lembur,
                gaji.hari_lembur,
                int(gaji.lembur_dibayar),
                gaji.gaji_lembur,
                gaji.tunjangan_obat,
                gaji.tunjangan_dinas,
                gaji.uang_terima_kasih,
                gaji.pot_alpa,
                gaji.koreksi_absensi,
                gaji.koreksi_admin,
                gaji.pot_bpjs_jht,
                gaji.pot_bpjs_jp,
                gaji.pot_bpjs_kesehatan,
                gaji.total_pot_bpjs,
                gaji.beban_bpjs_kesehatan,
                gaji.beban_bpjs_jht,
                gaji.beban_bpjs_jp,
                gaji.beban_bpjs_jkm,
                gaji.beban_bjps_jkk,
                gaji.total_beban_bpjs,
                gaji.total_bpjs_benefit,
                gaji.status_k_tk,
                gaji.ter_status,
                gaji.net_penghasilan,
                f'{gaji.persentase_pph21:.2f}',
                gaji.pot_pph21,
                gaji.total_gaji,
            ]
        )
    return '\ufeff' + buf.getvalue()
