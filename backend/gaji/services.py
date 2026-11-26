"""Build one employee's payroll snapshot for a month."""
from __future__ import annotations

import calendar
import csv
import io
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum

from absensi.models import Kehadiran, StatusKehadiran
from cuti.models import Cuti, TipeCuti
from karyawan.models import Karyawan, _completed_years
from koreksi.models import Koreksi, TipeKoreksi
from dinas.models import Dinas
from obat.models import TunjanganObat

from .lembur_bayar import hitung_lembur
from .models import Gaji
from .ter import ter_fraction

TUNJANGAN_DINAS_PER_HARI = 110_000
_JP_AGE_CUTOFF = 60

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
    sums = rows.aggregate(total_menit_telat=Sum('menit_telat'))
    return {
        'hari_hadir': rows.filter(status=StatusKehadiran.HADIR).count(),
        'hari_telat': rows.filter(menit_telat__gt=0).count(),
        'total_menit_telat': sums['total_menit_telat'] or 0,
        'hari_alpa': rows.filter(status=StatusKehadiran.ALPA).count(),
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
    return Dinas.objects.filter(
        karyawan=karyawan,
        tanggal__gte=start,
        tanggal__lte=end,
    ).count()


def _nominal_sum(queryset) -> int:
    return queryset.aggregate(total=Sum('nominal'))['total'] or 0


def _above_jp_age(karyawan: Karyawan, on: date) -> bool:
    """True once completed age from tanggal_lahir is over 60 on ``on``."""
    if karyawan.tanggal_lahir is None:
        return False
    return _completed_years(karyawan.tanggal_lahir, on) > _JP_AGE_CUTOFF


def build_gaji(karyawan: Karyawan, periode: date) -> Gaji:
    """Fill a new payroll row for this employee and month. The caller saves it."""
    start, end = month_bounds(periode)
    gaji = Gaji(karyawan=karyawan, periode=start)

    gaji.level = karyawan.level
    gaji.jabatan = karyawan.jabatan
    gaji.lembur_dibayar = karyawan.lembur_dibayar
    gaji.status_k_tk = karyawan.status_k_tk
    gaji.base_gaji_bpjs = int(karyawan.base_gaji)
    gaji.gaji_bulanan = int(karyawan.gaji_bulanan)

    for field, value in _attendance(karyawan, start, end).items():
        setattr(gaji, field, value)
    lembur = hitung_lembur(karyawan, start, end)
    gaji.jam_lembur = lembur.jam
    gaji.hari_lembur = lembur.hari
    for field, value in _leave_days(karyawan, start, end).items():
        setattr(gaji, field, value)
    gaji.hari_dinas = _hari_dinas(karyawan, start, end)

    gaji.tunjangan_obat = _nominal_sum(
        TunjanganObat.objects.filter(karyawan=karyawan, bulan=start)
    )
    gaji.koreksi_absensi = _nominal_sum(
        Koreksi.objects.filter(
            karyawan=karyawan, tanggal=start, tipe=TipeKoreksi.ABSENSI
        )
    )
    gaji.koreksi_admin = _nominal_sum(
        Koreksi.objects.filter(
            karyawan=karyawan, tanggal=start, tipe=TipeKoreksi.ADMIN
        )
    )

    if karyawan.absensi_dihitung:
        pot_alpa = Decimal(gaji.hari_alpa) * Decimal(gaji.gaji_bulanan) / Decimal(20)
    else:
        pot_alpa = Decimal(0)
    gaji_lembur = lembur.gaji
    tunjangan_dinas = Decimal(gaji.hari_dinas) * Decimal(TUNJANGAN_DINAS_PER_HARI)
    uang_terima_kasih = Decimal(0)

    has_bpjs = bool((karyawan.no_bpjs or '').strip())
    if has_bpjs:
        base = Decimal(gaji.base_gaji_bpjs)
        bpjs = {field: base * rate for field, rate in _BPJS_OF_BASE}
        if _above_jp_age(karyawan, end):
            bpjs['pot_bpjs_jp'] = Decimal(0)
            bpjs['beban_bpjs_jp'] = Decimal(0)
    else:
        bpjs = {field: Decimal(0) for field, _rate in _BPJS_OF_BASE}

    benefit = (
        bpjs['beban_bpjs_kesehatan']
        + bpjs['beban_bpjs_jkm']
        + bpjs['beban_bjps_jkk']
    )
    # Tax base stays exact. Tunjangan dinas, lembur, obat, koreksi, and the
    # other wage components are all inside this sum; none of them is rounded first.
    net = (
        Decimal(gaji.gaji_bulanan)
        + benefit
        + gaji_lembur
        + Decimal(gaji.tunjangan_obat)
        + tunjangan_dinas
        - pot_alpa
        + Decimal(gaji.koreksi_absensi)
        + Decimal(gaji.koreksi_admin)
        + uang_terima_kasih
    )
    if has_bpjs:
        fraction = ter_fraction(gaji.ter_status, net)
        pph = net * fraction
        gaji.persentase_pph21 = (fraction * Decimal(100)).quantize(Decimal('0.01'))
    else:
        pph = Decimal(0)
        gaji.persentase_pph21 = Decimal('0.00')
    # Employee BPJS is withheld from take-home. Like benefit and pph, it comes
    # off the exact amounts; the components are rounded only when stored.
    pot_bpjs = (
        bpjs['pot_bpjs_jht'] + bpjs['pot_bpjs_jp'] + bpjs['pot_bpjs_kesehatan']
    )
    total = net - benefit - pph - pot_bpjs

    gaji.pot_alpa = round_half_up(pot_alpa)
    gaji.gaji_lembur = round_half_up(gaji_lembur)
    gaji.tunjangan_dinas = round_half_up(tunjangan_dinas)
    gaji.uang_terima_kasih = round_half_up(uang_terima_kasih)
    for field, amount in bpjs.items():
        setattr(gaji, field, round_half_up(amount))
    gaji.pot_pph21 = round_half_up(pph)
    gaji.total_gaji = round_half_up(max(Decimal(0), total))
    return gaji


def write_gaji(karyawan: Karyawan, periode: date) -> Gaji:
    """Replace every payroll row for this employee and month with a new one.

    Unpaid overtime hours are added to ``akumulasi_lembur``. The previous
    row's ``jam_diakumulasi`` is removed first, so running this again for the
    same month replaces that month's hours.
    """
    start, end = month_bounds(periode)
    with transaction.atomic():
        locked = Karyawan.objects.select_for_update().get(pk=karyawan.pk)
        month_rows = Gaji.objects.filter(
            karyawan=locked,
            periode__gte=start,
            periode__lte=end,
        )
        previous = month_rows.aggregate(total=Sum('jam_diakumulasi'))['total'] or 0
        month_rows.delete()
        gaji = build_gaji(locked, periode)
        credited = 0 if locked.lembur_dibayar else gaji.jam_lembur
        gaji.jam_diakumulasi = credited
        gaji.save()
        locked.akumulasi_lembur = max(0, locked.akumulasi_lembur - previous + credited)
        locked.save(update_fields=['akumulasi_lembur'])
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
