"""Excel workbook that redoes ``build_gaji`` step by step with live formulas.

Inputs are written as plain values. Every step after that is an Excel formula
that mirrors the matching line in ``services.build_gaji``, so each column shows
how one number was derived from the columns before it.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from typing import Callable

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from karyawan.models import _completed_years

from .services import (
    _BPJS_OF_BASE,
    _JP_AGE_CUTOFF,
    TUNJANGAN_DINAS_PER_HARI,
    gaji_for_month,
    month_bounds,
)
from .ter import TER_BRACKETS

SHEET_DIAGNOSTIK = 'Diagnostik'
SHEET_KONSTANTA = 'Konstanta'
SHEET_TER = 'TER'

# Stand-in for the open top bracket (``None`` maximum).
TER_NO_CEILING = 10**18

_JP_FIELDS = frozenset({'pot_bpjs_jp', 'beban_bpjs_jp'})
_BENEFIT_FIELDS = ('beban_bpjs_kesehatan', 'beban_bpjs_jkm', 'beban_bjps_jkk')
_POT_FIELDS = ('pot_bpjs_jht', 'pot_bpjs_jp', 'pot_bpjs_kesehatan')
_BEBAN_FIELDS = (
    'beban_bpjs_jht',
    'beban_bpjs_jp',
    'beban_bpjs_kesehatan',
    'beban_bpjs_jkm',
    'beban_bjps_jkk',
)

FMT_MONEY = '#,##0'
FMT_EXACT = '#,##0.0000'
FMT_FRACTION = '0.0000'
FMT_PERCENT = '0.00'

INPUT = 'input'
STEP = 'step'
FINAL = 'final'

_HEADER_FILLS = {
    INPUT: PatternFill('solid', fgColor='DDEBF7'),
    STEP: PatternFill('solid', fgColor='FFF2CC'),
    FINAL: PatternFill('solid', fgColor='E2EFDA'),
}

Ref = Callable[[str], str]


@dataclass(frozen=True)
class Column:
    key: str
    kind: str
    number_format: str | None = None
    value: Callable | None = None
    formula: Callable[[Ref], str] | None = None


def _konstanta_rows() -> list[tuple[str, object, str | None]]:
    rows: list[tuple[str, object, str | None]] = [
        ('TUNJANGAN_DINAS_PER_HARI', TUNJANGAN_DINAS_PER_HARI, FMT_MONEY),
        ('JP_AGE_CUTOFF', _JP_AGE_CUTOFF, None),
    ]
    for field, rate in _BPJS_OF_BASE:
        rows.append((f'rate_{field}', float(rate), FMT_FRACTION))
    return rows


def _konstanta_refs() -> dict[str, str]:
    return {
        name: f"{SHEET_KONSTANTA}!$B${index}"
        for index, (name, _value, _fmt) in enumerate(_konstanta_rows(), start=2)
    }


def _ter_rows() -> list[tuple[str, int, int, float]]:
    rows = []
    for category, brackets in TER_BRACKETS.items():
        for minimum, maximum, rate in brackets:
            rows.append(
                (
                    category,
                    minimum,
                    TER_NO_CEILING if maximum is None else maximum,
                    float(rate),
                )
            )
    return rows


def _ter_formula(ter: str, net: str, has_bpjs: str) -> str:
    last = len(_ter_rows()) + 1
    cat = f'{SHEET_TER}!$A$2:$A${last}'
    lo = f'{SHEET_TER}!$B$2:$B${last}'
    hi = f'{SHEET_TER}!$C$2:$C${last}'
    tarif = f'{SHEET_TER}!$D$2:$D${last}'
    return (
        f'=IF(OR({has_bpjs}<>1,{ter}="",{net}<=0),0,'
        f'SUMPRODUCT(({cat}={ter})*({lo}<{net})*({hi}>={net})*{tarif}))'
    )


def _umur(gaji, end: date):
    lahir = gaji.karyawan.tanggal_lahir
    if lahir is None:
        return None
    return _completed_years(lahir, end)


def _columns(end: date) -> list[Column]:
    k = _konstanta_refs()

    cols = [
        Column('karyawan_id', INPUT, value=lambda g: g.karyawan_id),
        Column('nama', INPUT, value=lambda g: g.karyawan.nama),
        Column('periode', INPUT, value=lambda g: f'{g.periode:%Y-%m}'),
        Column('status_k_tk', INPUT, value=lambda g: g.status_k_tk),
        Column('ter_status', INPUT, value=lambda g: g.ter_status),
        Column(
            'has_bpjs',
            INPUT,
            value=lambda g: int(bool((g.karyawan.no_bpjs or '').strip())),
        ),
        Column(
            'absensi_dihitung',
            INPUT,
            value=lambda g: int(g.karyawan.absensi_dihitung),
        ),
        Column('umur', INPUT, value=lambda g: _umur(g, end)),
        Column('hari_alpa', INPUT, value=lambda g: g.hari_alpa),
        Column('hari_dinas', INPUT, value=lambda g: g.hari_dinas),
        Column('base_gaji_bpjs', INPUT, FMT_MONEY, value=lambda g: g.base_gaji_bpjs),
        Column('gaji_bulanan', INPUT, FMT_MONEY, value=lambda g: g.gaji_bulanan),
        Column('tunjangan_obat', INPUT, FMT_MONEY, value=lambda g: g.tunjangan_obat),
        Column(
            'koreksi_absensi', INPUT, FMT_MONEY, value=lambda g: g.koreksi_absensi
        ),
        Column('koreksi_admin', INPUT, FMT_MONEY, value=lambda g: g.koreksi_admin),
        Column(
            'pot_alpa_exact',
            STEP,
            FMT_EXACT,
            formula=lambda c: (
                f'=IF({c("absensi_dihitung")}=1,'
                f'{c("hari_alpa")}*{c("gaji_bulanan")}/20,0)'
            ),
        ),
        Column('gaji_lembur_exact', STEP, FMT_EXACT, formula=lambda c: '=0'),
        Column(
            'tunjangan_dinas_exact',
            STEP,
            FMT_EXACT,
            formula=lambda c: (
                f'={c("hari_dinas")}*{k["TUNJANGAN_DINAS_PER_HARI"]}'
            ),
        ),
        Column('uang_terima_kasih_exact', STEP, FMT_EXACT, formula=lambda c: '=0'),
        Column(
            'jp_lewat_umur',
            STEP,
            formula=lambda c: (
                f'=AND({c("umur")}<>"",{c("umur")}>{k["JP_AGE_CUTOFF"]})'
            ),
        ),
    ]

    for field, _rate in _BPJS_OF_BASE:
        rate_ref = k[f'rate_{field}']

        def bpjs_formula(c, rate_ref=rate_ref, field=field):
            amount = f'IF({c("has_bpjs")}=1,{c("base_gaji_bpjs")}*{rate_ref},0)'
            if field in _JP_FIELDS:
                amount = f'IF({c("jp_lewat_umur")},0,{amount})'
            return f'={amount}'

        cols.append(Column(f'{field}_exact', STEP, FMT_EXACT, formula=bpjs_formula))

    cols += [
        Column(
            'benefit_exact',
            STEP,
            FMT_EXACT,
            formula=lambda c: '=' + '+'.join(c(f'{f}_exact') for f in _BENEFIT_FIELDS),
        ),
        Column(
            'net_exact',
            STEP,
            FMT_EXACT,
            formula=lambda c: (
                f'={c("gaji_bulanan")}'
                f'+{c("benefit_exact")}'
                f'+{c("gaji_lembur_exact")}'
                f'+{c("tunjangan_obat")}'
                f'+{c("tunjangan_dinas_exact")}'
                f'-{c("pot_alpa_exact")}'
                f'+{c("koreksi_absensi")}'
                f'+{c("koreksi_admin")}'
                f'+{c("uang_terima_kasih_exact")}'
            ),
        ),
        Column(
            'ter_fraction',
            STEP,
            FMT_FRACTION,
            formula=lambda c: _ter_formula(
                c('ter_status'), c('net_exact'), c('has_bpjs')
            ),
        ),
        Column(
            'pph_exact',
            STEP,
            FMT_EXACT,
            formula=lambda c: f'={c("net_exact")}*{c("ter_fraction")}',
        ),
        Column(
            'total_exact',
            STEP,
            FMT_EXACT,
            formula=lambda c: (
                f'={c("net_exact")}-{c("benefit_exact")}-{c("pph_exact")}'
            ),
        ),
    ]

    def rounded(key: str, source: str) -> Column:
        return Column(
            key, FINAL, FMT_MONEY, formula=lambda c: f'=ROUND({c(source)},0)'
        )

    cols += [
        rounded('pot_alpa', 'pot_alpa_exact'),
        rounded('gaji_lembur', 'gaji_lembur_exact'),
        rounded('tunjangan_dinas', 'tunjangan_dinas_exact'),
        rounded('uang_terima_kasih', 'uang_terima_kasih_exact'),
    ]
    cols += [rounded(field, f'{field}_exact') for field, _rate in _BPJS_OF_BASE]

    def summed(key: str, fields) -> Column:
        return Column(
            key,
            FINAL,
            FMT_MONEY,
            formula=lambda c: '=' + '+'.join(c(f) for f in fields),
        )

    cols += [
        summed('total_pot_bpjs', _POT_FIELDS),
        summed('total_beban_bpjs', _BEBAN_FIELDS),
        summed('total_bpjs_benefit', _BENEFIT_FIELDS),
        Column(
            'net_penghasilan',
            FINAL,
            FMT_MONEY,
            formula=lambda c: (
                f'={c("gaji_bulanan")}'
                f'+{c("total_bpjs_benefit")}'
                f'+{c("gaji_lembur")}'
                f'+{c("tunjangan_obat")}'
                f'+{c("tunjangan_dinas")}'
                f'-{c("pot_alpa")}'
                f'+{c("koreksi_absensi")}'
                f'+{c("koreksi_admin")}'
                f'+{c("uang_terima_kasih")}'
            ),
        ),
        Column(
            'persentase_pph21',
            FINAL,
            FMT_PERCENT,
            formula=lambda c: f'=ROUND({c("ter_fraction")}*100,2)',
        ),
        rounded('pot_pph21', 'pph_exact'),
        Column(
            'total_gaji',
            FINAL,
            FMT_MONEY,
            formula=lambda c: f'=ROUND(MAX(0,{c("total_exact")}),0)',
        ),
    ]
    return cols


def _write_header(ws, titles: list[str]) -> None:
    bold = Font(bold=True)
    for col, title in enumerate(titles, start=1):
        ws.cell(row=1, column=col, value=title).font = bold


def _write_konstanta(ws) -> None:
    _write_header(ws, ['nama', 'nilai'])
    for row, (name, value, fmt) in enumerate(_konstanta_rows(), start=2):
        ws.cell(row=row, column=1, value=name)
        cell = ws.cell(row=row, column=2, value=value)
        if fmt:
            cell.number_format = fmt
    ws.column_dimensions['A'].width = 34
    ws.column_dimensions['B'].width = 16


def _write_ter(ws) -> None:
    _write_header(ws, ['kategori', 'min', 'max', 'tarif'])
    for row, (category, minimum, maximum, rate) in enumerate(_ter_rows(), start=2):
        ws.cell(row=row, column=1, value=category)
        ws.cell(row=row, column=2, value=minimum).number_format = FMT_MONEY
        ws.cell(row=row, column=3, value=maximum).number_format = FMT_MONEY
        ws.cell(row=row, column=4, value=rate).number_format = FMT_FRACTION
    for letter, width in (('A', 10), ('B', 26), ('C', 26), ('D', 10)):
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = 'A2'


def _write_diagnostik(ws, rows, columns: list[Column]) -> None:
    letters = {
        col.key: get_column_letter(index)
        for index, col in enumerate(columns, start=1)
    }
    _write_header(ws, [col.key for col in columns])
    for index, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=index)
        cell.fill = _HEADER_FILLS[col.kind]
        ws.column_dimensions[letters[col.key]].width = max(14, len(col.key) + 2)

    for row, gaji in enumerate(rows, start=2):
        def ref(key: str, row=row) -> str:
            return f'{letters[key]}{row}'

        for index, col in enumerate(columns, start=1):
            if col.formula is not None:
                value = col.formula(ref)
            else:
                value = col.value(gaji)
            cell = ws.cell(row=row, column=index, value=value)
            if col.number_format:
                cell.number_format = col.number_format

    ws.freeze_panes = 'C2'


def build_diagnostik_workbook(periode: date) -> Workbook:
    start, end = month_bounds(periode)
    wb = Workbook()
    diag = wb.active
    diag.title = SHEET_DIAGNOSTIK
    _write_diagnostik(diag, gaji_for_month(start), _columns(end))
    _write_konstanta(wb.create_sheet(SHEET_KONSTANTA))
    _write_ter(wb.create_sheet(SHEET_TER))
    return wb


def export_gaji_diagnostik_xlsx(periode: date) -> bytes:
    buf = io.BytesIO()
    build_diagnostik_workbook(periode).save(buf)
    return buf.getvalue()
