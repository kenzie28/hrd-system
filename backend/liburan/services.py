"""CSV import for Liburan (nama, tanggal)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

from django.db import transaction

from .models import Liburan

COL_NAMA = 'nama'
COL_TANGGAL = 'tanggal'
REQUIRED_COLUMNS = [COL_NAMA, COL_TANGGAL]


@dataclass
class LiburanImportError:
    row: int
    message: str


@dataclass
class LiburanImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[LiburanImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_liburan_import_result(result: LiburanImportResult) -> dict:
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
    # Header is usually short; prefer the delimiter that appears more often.
    if first_line.count(';') > first_line.count(','):
        return ';'
    return ','


def _parse_tanggal(value: str) -> date | None:
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def import_liburan_csv(upload) -> LiburanImportResult:
    """Validate and create Liburan rows from a CSV with columns nama,tanggal.

    Delimiter may be comma or semicolon (auto-detected). All rows are
    validated before any write. On validation errors nothing is persisted.
    """
    result = LiburanImportResult()

    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8-sig')
        else:
            text = str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            LiburanImportError(0, 'File harus berformat UTF-8.')
        )
        return result

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            LiburanImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    header_set = set(headers)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        result.errors.append(
            LiburanImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    to_create: list[Liburan] = []
    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        nama = (row.get(COL_NAMA) or '').strip()
        tanggal_raw = (row.get(COL_TANGGAL) or '').strip()

        if not nama:
            result.errors.append(
                LiburanImportError(row_num, 'Kolom nama wajib diisi.')
            )
            continue
        if len(nama) > 64:
            result.errors.append(
                LiburanImportError(
                    row_num, 'Nama maksimal 64 karakter.'
                )
            )
            continue

        tanggal = _parse_tanggal(tanggal_raw)
        if tanggal is None:
            result.errors.append(
                LiburanImportError(
                    row_num,
                    f'tanggal harus format yyyy-mm-dd (diterima: "{tanggal_raw}").',
                )
            )
            continue

        to_create.append(Liburan(nama=nama, tanggal=tanggal))

    if result.errors:
        return result

    if not to_create:
        result.errors.append(
            LiburanImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    with transaction.atomic():
        Liburan.objects.bulk_create(to_create)
    result.created = len(to_create)
    return result
