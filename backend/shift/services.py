"""CSV import for Shift (lokasi_kerja, hari, jam_masuk, jam_keluar)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, time

from django.db import transaction

from core.models import Lokasi

from .models import HariKerja, Shift

COL_LOKASI = 'lokasi_kerja'
COL_HARI = 'hari'
COL_JAM_MASUK = 'jam_masuk'
COL_JAM_KELUAR = 'jam_keluar'
REQUIRED_COLUMNS = [COL_LOKASI, COL_HARI, COL_JAM_MASUK, COL_JAM_KELUAR]

# Accept either the stored code (SENIN) or the Indonesian label (Senin), case-insensitive.
_HARI_LOOKUP: dict[str, str] = {}
for _value, _label in HariKerja.choices:
    _HARI_LOOKUP[_value.upper()] = _value
    _HARI_LOOKUP[_label.upper()] = _value


@dataclass
class ShiftImportError:
    row: int
    message: str


@dataclass
class ShiftImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[ShiftImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_shift_import_result(result: ShiftImportResult) -> dict:
    """JSON-serializable import outcome for the admin-frontend."""
    return {
        'ok': result.ok,
        'total_rows': result.total_rows,
        'created': result.created,
        'errors': [{'row': e.row, 'message': e.message} for e in result.errors],
        'received_headers': result.received_headers,
        'required_columns': REQUIRED_COLUMNS,
    }


def _detect_delimiter(text: str) -> str:
    """Pick comma or semicolon from the header line (Excel-friendly)."""
    first_line = next((line for line in text.splitlines() if line.strip()), '')
    if not first_line:
        return ','
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=',;')
        if dialect.delimiter in (',', ';'):
            return dialect.delimiter
    except csv.Error:
        pass
    if first_line.count(';') > first_line.count(','):
        return ';'
    return ','


def _parse_hari(value: str) -> str | None:
    return _HARI_LOOKUP.get((value or '').strip().upper())


def _parse_time(value: str) -> time | None:
    value = (value or '').strip()
    if not value:
        return None
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def import_shift_csv(upload) -> ShiftImportResult:
    """Validate and create Shift rows from a CSV with columns
    lokasi_kerja,hari,jam_masuk,jam_keluar.

    lokasi_kerja must reference an existing Lokasi. hari accepts either the
    stored code (SENIN) or the Indonesian label (Senin), case-insensitive.
    jam_masuk/jam_keluar accept HH:MM or HH:MM:SS. Delimiter may be comma or
    semicolon (auto-detected). All rows are validated before any write.
    """
    result = ShiftImportResult()

    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8-sig')
        else:
            text = str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            ShiftImportError(0, 'File harus berformat UTF-8.')
        )
        return result

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            ShiftImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    header_set = set(headers)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        result.errors.append(
            ShiftImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    lokasi_cache: dict[str, Lokasi | None] = {}
    to_create: list[Shift] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        lokasi_id = (row.get(COL_LOKASI) or '').strip()
        hari_raw = (row.get(COL_HARI) or '').strip()
        jam_masuk_raw = (row.get(COL_JAM_MASUK) or '').strip()
        jam_keluar_raw = (row.get(COL_JAM_KELUAR) or '').strip()

        if not lokasi_id:
            result.errors.append(
                ShiftImportError(row_num, 'Kolom lokasi_kerja wajib diisi.')
            )
            continue
        if lokasi_id not in lokasi_cache:
            lokasi_cache[lokasi_id] = Lokasi.objects.filter(pk=lokasi_id).first()
        lokasi = lokasi_cache[lokasi_id]
        if lokasi is None:
            result.errors.append(
                ShiftImportError(
                    row_num,
                    f'lokasi_kerja "{lokasi_id}" tidak ditemukan.',
                )
            )
            continue

        hari = _parse_hari(hari_raw)
        if hari is None:
            result.errors.append(
                ShiftImportError(
                    row_num,
                    f'hari harus salah satu dari Senin–Minggu (diterima: "{hari_raw}").',
                )
            )
            continue

        jam_masuk = _parse_time(jam_masuk_raw)
        if jam_masuk is None:
            result.errors.append(
                ShiftImportError(
                    row_num,
                    f'jam_masuk harus format HH:MM (diterima: "{jam_masuk_raw}").',
                )
            )
            continue

        jam_keluar = _parse_time(jam_keluar_raw)
        if jam_keluar is None:
            result.errors.append(
                ShiftImportError(
                    row_num,
                    f'jam_keluar harus format HH:MM (diterima: "{jam_keluar_raw}").',
                )
            )
            continue

        to_create.append(
            Shift(
                lokasi_kerja=lokasi,
                hari=hari,
                jam_masuk=jam_masuk,
                jam_keluar=jam_keluar,
            )
        )

    if result.errors:
        return result

    if not to_create:
        result.errors.append(
            ShiftImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    with transaction.atomic():
        Shift.objects.bulk_create(to_create)
    result.created = len(to_create)
    return result
