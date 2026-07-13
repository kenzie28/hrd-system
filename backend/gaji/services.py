"""CSV import for GajiTemp.

Parses a payroll CSV in the same format as ``gaji-input.csv`` (repo root)
and upserts one ``GajiTemp`` row per (karyawan, periode). See the column
mapping table in the module-level constants below.

Every row is validated — including that its Karyawan can be resolved —
before anything is written. If any row fails validation, nothing is
persisted and the full list of errors is returned so the CSV can be fixed
and re-uploaded.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from core.models import Karyawan

from .models import GajiTemp
from .temp_karyawan_upsert import upsert_karyawan_from_gaji_row

# Column headers exactly as they appear in the HRD payroll CSV export,
# after stripping surrounding whitespace. Columns not listed here (e.g.
# "Total H/S/C", "Target Hadir", "UMP Hadir", "Total Gaji+Tlk+Incent",
# "U.LEMBUR+Raya") are legacy derived reference numbers in the export and
# are intentionally not imported — GajiTemp computes its own equivalents.
COL_NO_ID = 'NO.ID'
COL_NAMA = 'NAMA KARYAWAN'
COL_JABATAN = 'JABATAN'
COL_LOKASI = 'Lokasi Kerja'
COL_PERIODE = 'Periode'
COL_WILAYAH = 'Wilayah'
COL_HADIR = 'HADIR'
COL_SK_CU_CT = 'SK/CU/CT'
COL_AL = 'AL'
COL_FREQ_TARGET = 'Freq.Tercapai Personal'
COL_RATE_TARGET = 'Rate Target'
COL_RATE_UMP = 'Rate UMP+'
COL_GAJI = 'Gaji'
COL_TLM_KERJA = 'TLM Kerja'
COL_LEMBUR = 'Lembur'
COL_RATE_LEMBUR = 'Rate Lembur/6Jam'
COL_RY = 'RY'
COL_TUNJ_OBAT = 'TUNJ OBAT'
COL_KOREKSI_ADMIN = 'Koreksi Admin'
COL_KOREKSI_ABSENSI = 'Koreksi Absensi'
COL_PREMI_JHT = 'Premi JHT TK'
COL_PREMI_JP = 'Premi JP TK'
COL_F1_BG = 'F1/BG Empl'
COL_PPH21 = 'PPh21 yg diSetor'
COL_NET_TRANSFER = 'Net.Transfer'
COL_TOTAL_TRF_UMAKAN = 'Total Trf.U.Makan'

REQUIRED_COLUMNS = [COL_NO_ID, COL_NAMA, COL_PERIODE, COL_HADIR]


@dataclass
class GajiImportError:
    row: int
    message: str


@dataclass
class GajiImportResult:
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    karyawan_created: int = 0
    errors: list[GajiImportError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _strip_quote(value: str) -> str:
    """Strip the leading ``'`` Excel-text marker some CSV columns use."""
    value = (value or '').strip()
    return value[1:].strip() if value.startswith("'") else value


def _parse_int(value: str) -> int:
    value = _strip_quote(value)
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def _parse_decimal(value: str) -> Decimal:
    value = _strip_quote(value)
    if not value:
        return Decimal('0')
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal('0')


def _split_triplet(value: str) -> tuple[int, int, int]:
    """Parse an ``X/Y/Z`` field (e.g. HADIR, SK/CU/CT): trim each part and
    convert to a number, defaulting blank parts to 0."""
    parts = _strip_quote(value).split('/')
    parts = (parts + ['', '', ''])[:3]
    x, y, z = (_parse_int(p) for p in parts)
    return x, y, z


def _format_karyawan_id(value: str) -> str:
    return _strip_quote(value).zfill(7)[-7:]


def _parse_periode(value: str) -> date | None:
    value = _strip_quote(value)
    if len(value) != 6 or not value.isdigit():
        return None
    year, month = int(value[:4]), int(value[4:])
    if not (1 <= month <= 12):
        return None
    return date(year, month, 1)


def _normalize_header(name: str) -> str:
    return (name or '').strip()


def _read_rows(fileobj) -> tuple[list[str], list[list[str]]]:
    content = fileobj.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(content)))
    if not rows:
        return [], []
    header = [_normalize_header(h) for h in rows[0]]
    return header, rows[1:]


def _row_dict(header: list[str], row: list[str]) -> dict[str, str]:
    return {header[i]: (row[i] if i < len(row) else '') for i in range(len(header))}


@dataclass
class _ParsedRow:
    row_number: int
    karyawan_id: str
    nama: str
    jabatan: str
    lokasi_id: str
    wilayah: str
    periode: date
    fields: dict


def _parse_row(
    row_number: int, data: dict[str, str], errors: list[GajiImportError]
) -> _ParsedRow | None:
    karyawan_id_raw = data.get(COL_NO_ID, '')
    if not _strip_quote(karyawan_id_raw):
        errors.append(GajiImportError(row_number, 'NO.ID kosong.'))
        return None
    karyawan_id = _format_karyawan_id(karyawan_id_raw)

    periode = _parse_periode(data.get(COL_PERIODE, ''))
    if periode is None:
        errors.append(
            GajiImportError(
                row_number, f'Periode tidak valid: {data.get(COL_PERIODE, "")!r}'
            )
        )
        return None

    hadir_x, hadir_y, hadir_z = _split_triplet(data.get(COL_HADIR, ''))
    hadir = hadir_x + hadir_y + hadir_z
    hari_sakit, hari_cuti, hari_cuti_tambahan = _split_triplet(
        data.get(COL_SK_CU_CT, '')
    )

    fields = dict(
        hadir=hadir,
        hari_sakit=hari_sakit,
        hari_cuti=hari_cuti,
        hari_cuti_tambahan=hari_cuti_tambahan,
        freq_pencapaian_target=_parse_int(data.get(COL_FREQ_TARGET, '')),
        rate_target=_parse_int(data.get(COL_RATE_TARGET, '')),
        rate_non_target=_parse_int(data.get(COL_RATE_UMP, '')),
        gaji_pokok=_parse_int(data.get(COL_GAJI, '')),
        freq_lembur_6_jam=_parse_decimal(data.get(COL_LEMBUR, '')),
        rate_lembur_6_jam=_parse_int(data.get(COL_RATE_LEMBUR, '')),
        freq_hari_raya=_parse_int(data.get(COL_RY, '')),
        tunjangan_lama_kerja=_parse_int(data.get(COL_TLM_KERJA, '')),
        tunjangan_obat=_parse_int(data.get(COL_TUNJ_OBAT, '')),
        freq_alpa=_parse_int(data.get(COL_AL, '')),
        pot_bpjs_jht=-_parse_int(data.get(COL_PREMI_JHT, '')),
        pot_bpjs_jp=-_parse_int(data.get(COL_PREMI_JP, '')),
        pot_bpjs_kesehatan=-_parse_int(data.get(COL_F1_BG, '')),
        pot_pph21=-_parse_int(data.get(COL_PPH21, '')),
        pot_kehilangan=_parse_int(data.get(COL_KOREKSI_ADMIN, '')),
        koreksi_absensi=_parse_int(data.get(COL_KOREKSI_ABSENSI, '')),
        total_gaji=(
            _parse_int(data.get(COL_NET_TRANSFER, ''))
            + _parse_int(data.get(COL_TOTAL_TRF_UMAKAN, ''))
        ),
    )

    return _ParsedRow(
        row_number=row_number,
        karyawan_id=karyawan_id,
        nama=_strip_quote(data.get(COL_NAMA, '')),
        jabatan=_strip_quote(data.get(COL_JABATAN, '')),
        lokasi_id=_strip_quote(data.get(COL_LOKASI, '')),
        wilayah=_strip_quote(data.get(COL_WILAYAH, '')),
        periode=periode,
        fields=fields,
    )


def _resolve_karyawan(
    parsed: _ParsedRow, *, upsert_karyawan: bool
) -> tuple[Karyawan | None, bool]:
    if upsert_karyawan:
        return upsert_karyawan_from_gaji_row(
            karyawan_id=parsed.karyawan_id,
            nama=parsed.nama,
            jabatan=parsed.jabatan,
            lokasi_id=parsed.lokasi_id,
            wilayah=parsed.wilayah,
        )
    return Karyawan.objects.filter(karyawan_id=parsed.karyawan_id).first(), False


def import_gaji_csv(fileobj, *, upsert_karyawan: bool = True) -> GajiImportResult:
    result = GajiImportResult()
    header, raw_rows = _read_rows(fileobj)

    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        result.errors.append(
            GajiImportError(0, f'Kolom wajib tidak ditemukan: {", ".join(missing)}')
        )
        return result

    parsed_rows: list[_ParsedRow] = []
    for i, raw_row in enumerate(raw_rows, start=2):  # row 1 is the header
        if not any(cell.strip() for cell in raw_row):
            continue
        data = _row_dict(header, raw_row)
        result.total_rows += 1
        parsed = _parse_row(i, data, result.errors)
        if parsed is not None:
            parsed_rows.append(parsed)

    if result.errors:
        return result

    with transaction.atomic():
        karyawan_cache: dict[str, Karyawan] = {}
        for parsed in parsed_rows:
            if parsed.karyawan_id in karyawan_cache:
                continue
            karyawan, created = _resolve_karyawan(
                parsed, upsert_karyawan=upsert_karyawan
            )
            if karyawan is None:
                result.errors.append(
                    GajiImportError(
                        parsed.row_number,
                        f'Karyawan dengan NO.ID {parsed.karyawan_id} tidak ditemukan.',
                    )
                )
                continue
            karyawan_cache[parsed.karyawan_id] = karyawan
            if created:
                result.karyawan_created += 1

        if result.errors:
            transaction.set_rollback(True)
            return result

        for parsed in parsed_rows:
            karyawan = karyawan_cache[parsed.karyawan_id]
            _, created = GajiTemp.objects.update_or_create(
                karyawan=karyawan,
                periode=parsed.periode,
                defaults=parsed.fields,
            )
            if created:
                result.created += 1
            else:
                result.updated += 1

    return result
