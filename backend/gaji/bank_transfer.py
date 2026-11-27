"""Excel workbook of one month's payroll for bank transfer."""
from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from typing import Callable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from karyawan.models import _completed_years

from .services import gaji_for_month, month_bounds

SHEET_BANK_TRANSFER = 'Bank Transfer'

GROUP_POTONGAN = 'Potongan BPJS'
GROUP_BEBAN = 'Beban BPJS Perusahaan'

FMT_TEXT = '@'
FMT_MONEY = '#,##0'
FMT_PERCENT = '0.00'
FMT_INT = '0'

_FILL_HEADER = PatternFill('solid', fgColor='D6DCE4')
_FILL_POTONGAN = PatternFill('solid', fgColor='F8CBAD')
_FILL_BEBAN = PatternFill('solid', fgColor='C6EFCE')
_GROUP_FILLS = {
    GROUP_POTONGAN: _FILL_POTONGAN,
    GROUP_BEBAN: _FILL_BEBAN,
}

_THIN = Border(
    left=Side(style='thin', color='BFBFBF'),
    right=Side(style='thin', color='BFBFBF'),
    top=Side(style='thin', color='BFBFBF'),
    bottom=Side(style='thin', color='BFBFBF'),
)
_HEADER_FONT = Font(bold=True, name='Calibri', size=10, color='1F2933')
_DATA_FONT = Font(name='Calibri', size=10, color='1F2933')
_HEADER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)


@dataclass(frozen=True)
class _Column:
    title: str
    value: Callable
    group: str | None = None
    number_format: str | None = None
    align: str = 'right'
    width: float = 14


def _text(value) -> str | None:
    text = ('' if value is None else str(value)).strip()
    return text or None


def _has_bpjs(karyawan) -> bool:
    return bool((karyawan.no_bpjs or '').strip())


def _lama_kerja(karyawan, end: date):
    """Completed years as of the payroll month, stopping early on exit."""
    if karyawan.tanggal_awal is None:
        return None
    stop = end
    if karyawan.tanggal_keluar is not None and karyawan.tanggal_keluar < end:
        stop = karyawan.tanggal_keluar
    return _completed_years(karyawan.tanggal_awal, stop)


def _umur(karyawan, end: date):
    if karyawan.tanggal_lahir is None:
        return None
    return _completed_years(karyawan.tanggal_lahir, end)


def _width(title: str, minimum: float) -> float:
    return max(minimum, min(len(title) + 2.5, 36))


def _col(title, value, *, group=None, fmt=None, align='right', minimum=12):
    return _Column(
        title=title,
        value=value,
        group=group,
        number_format=fmt,
        align=align,
        width=_width(title, minimum),
    )


def _columns(end: date) -> list[_Column]:
    def transfer_pt(gaji):
        if _has_bpjs(gaji.karyawan):
            return gaji.total_gaji
        return 0

    def transfer_ho(gaji):
        extra = 0 if _has_bpjs(gaji.karyawan) else gaji.total_gaji
        return gaji.gaji_tambahan + extra

    text = dict(fmt=FMT_TEXT, align='left')
    money = dict(fmt=FMT_MONEY, minimum=15)
    count = dict(fmt=FMT_INT, minimum=12)
    return [
        _col('ID Karyawan', lambda g: g.karyawan_id, minimum=14, **text),
        _col('Nama', lambda g: g.karyawan.nama, minimum=28, **text),
        _col('Level', lambda g: g.level, **count),
        _col('Jabatan', lambda g: _text(g.jabatan), minimum=22, **text),
        _col(
            'Percobaan Jabatan',
            lambda g: 'Ya' if g.karyawan.percobaan_jabatan else 'Tidak',
            align='center',
            minimum=14,
        ),
        _col('Lama Kerja', lambda g: _lama_kerja(g.karyawan, end), **count),
        _col('Umur', lambda g: _umur(g.karyawan, end), **count),
        _col('No. BPJS', lambda g: _text(g.karyawan.no_bpjs), minimum=20, **text),
        _col('No. KPJ', lambda g: _text(g.karyawan.no_kpj), minimum=18, **text),
        _col('Hadir', lambda g: g.hari_hadir, **count),
        _col('Sakit', lambda g: g.hari_sakit, **count),
        _col('Cuti Tahunan', lambda g: g.hari_cuti_tahunan, **count),
        _col('Cuti Tambahan', lambda g: g.hari_cuti_tambahan, **count),
        _col('Alpa', lambda g: g.hari_alpa, **count),
        _col('Jam Lembur', lambda g: g.jam_lembur, **count),
        _col('Hari Lembur', lambda g: g.hari_lembur, **count),
        _col('Lembur Perjalanan Dinas', lambda g: g.hari_dinas, **count),
        _col('Gaji BPJS', lambda g: g.base_gaji_bpjs, **money),
        _col(
            'Kesehatan',
            lambda g: g.pot_bpjs_kesehatan,
            group=GROUP_POTONGAN,
            **money,
        ),
        _col('JHT', lambda g: g.pot_bpjs_jht, group=GROUP_POTONGAN, **money),
        _col('JP', lambda g: g.pot_bpjs_jp, group=GROUP_POTONGAN, **money),
        _col(
            'Kesehatan',
            lambda g: g.beban_bpjs_kesehatan,
            group=GROUP_BEBAN,
            **money,
        ),
        _col('JHT', lambda g: g.beban_bpjs_jht, group=GROUP_BEBAN, **money),
        _col('JP', lambda g: g.beban_bpjs_jp, group=GROUP_BEBAN, **money),
        _col('JKM', lambda g: g.beban_bpjs_jkm, group=GROUP_BEBAN, **money),
        _col('JKK', lambda g: g.beban_bjps_jkk, group=GROUP_BEBAN, **money),
        _col('Gaji Bulanan', lambda g: g.gaji_bulanan, **money),
        _col('Gaji Lembur', lambda g: g.gaji_lembur, **money),
        _col('Tunjangan Obat', lambda g: g.tunjangan_obat, **money),
        _col('Tunjangan Dinas', lambda g: g.tunjangan_dinas, **money),
        _col('Potongan Alpa', lambda g: g.pot_alpa, **money),
        _col('Koreksi Absensi', lambda g: g.koreksi_absensi, **money),
        _col('Koreksi Admin', lambda g: g.koreksi_admin, **money),
        _col('Uang Terima Kasih', lambda g: g.uang_terima_kasih, **money),
        _col('Net Penghasilan dikena Pajak', lambda g: g.net_penghasilan, **money),
        _col('Status K/TK', lambda g: _text(g.status_k_tk), minimum=12, **text),
        _col('Status TER', lambda g: _text(g.ter_status), minimum=12, **text),
        _col(
            'Persentase PPH21',
            lambda g: g.persentase_pph21,
            fmt=FMT_PERCENT,
            minimum=14,
        ),
        _col('Potongan PPH21', lambda g: g.pot_pph21, **money),
        _col('Total Gaji', lambda g: g.total_gaji, **money),
        _col('Gaji Tambahan', lambda g: g.gaji_tambahan, **money),
        _col('Transfer PT', transfer_pt, **money),
        _col('Transfer HO', transfer_ho, **money),
    ]


def _apply_header(cell, fill) -> None:
    cell.font = _HEADER_FONT
    cell.alignment = _HEADER_ALIGN
    cell.border = _THIN
    cell.fill = fill


def _write_headers(ws: Worksheet, columns: list[_Column]) -> None:
    for index, col in enumerate(columns, start=1):
        fill = _GROUP_FILLS.get(col.group, _FILL_HEADER)
        top = ws.cell(1, index, value=None if col.group else col.title)
        sub = ws.cell(2, index, value=col.title if col.group else None)
        _apply_header(top, fill)
        _apply_header(sub, fill)
        if col.group is None:
            ws.merge_cells(
                start_row=1, start_column=index, end_row=2, end_column=index
            )
        letter = get_column_letter(index)
        ws.column_dimensions[letter].width = col.width

    index = 0
    while index < len(columns):
        group = columns[index].group
        if group is None:
            index += 1
            continue
        end = index
        while end < len(columns) and columns[end].group == group:
            end += 1
        cell = ws.cell(1, index + 1, value=group)
        _apply_header(cell, _GROUP_FILLS[group])
        if end - index > 1:
            ws.merge_cells(
                start_row=1,
                start_column=index + 1,
                end_row=1,
                end_column=end,
            )
        index = end

    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    ws.freeze_panes = 'A3'
    ws.sheet_view.showGridLines = False


def _write_rows(ws: Worksheet, rows, columns: list[_Column]) -> None:
    for row_index, gaji in enumerate(rows, start=3):
        for index, col in enumerate(columns, start=1):
            cell = ws.cell(row_index, index, value=col.value(gaji))
            cell.font = _DATA_FONT
            cell.border = _THIN
            cell.alignment = Alignment(horizontal=col.align, vertical='center')
            if col.number_format:
                cell.number_format = col.number_format
        ws.row_dimensions[row_index].height = 18
    last_row = max(ws.max_row, 2)
    ws.auto_filter.ref = f'A2:{get_column_letter(len(columns))}{last_row}'


def build_bank_transfer_workbook(periode: date) -> Workbook:
    start, end = month_bounds(periode)
    columns = _columns(end)
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_BANK_TRANSFER
    ws.sheet_properties.tabColor = '1F4E79'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = '1:2'
    ws.page_setup.horizontalCentered = True
    ws.sheet_view.zoomScale = 110
    ws.oddHeader.left.text = f'Bank Transfer {start:%m-%Y}'
    _write_headers(ws, columns)
    _write_rows(ws, gaji_for_month(start), columns)
    return wb


def export_gaji_bank_transfer_xlsx(periode: date) -> bytes:
    buf = io.BytesIO()
    build_bank_transfer_workbook(periode).save(buf)
    return buf.getvalue()
