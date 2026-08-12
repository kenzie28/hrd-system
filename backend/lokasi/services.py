"""CSV import for Lokasi (id, nama)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from django.db import transaction

from .models import Lokasi

COL_ID = 'id'
COL_NAMA = 'nama'
REQUIRED_COLUMNS = [COL_ID, COL_NAMA]


@dataclass
class LokasiImportError:
    row: int
    message: str


@dataclass
class LokasiImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[LokasiImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_lokasi_import_result(result: LokasiImportResult) -> dict:
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


def import_lokasi_csv(upload) -> LokasiImportResult:
    """Validate and create Lokasi rows from a CSV with columns id,nama.

    Delimiter may be comma or semicolon (auto-detected). All rows are
    validated before any write. On validation errors nothing is persisted.
    """
    result = LokasiImportResult()

    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8-sig')
        else:
            text = str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            LokasiImportError(0, 'File harus berformat UTF-8.')
        )
        return result

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            LokasiImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    header_set = set(headers)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        result.errors.append(
            LokasiImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    existing_ids = set(Lokasi.objects.values_list('id', flat=True))
    seen_in_file: set[str] = set()
    to_create: list[Lokasi] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        lokasi_id = (row.get(COL_ID) or '').strip()
        nama = (row.get(COL_NAMA) or '').strip()

        if not lokasi_id:
            result.errors.append(
                LokasiImportError(row_num, 'Kolom id wajib diisi.')
            )
            continue
        if len(lokasi_id) > 2:
            result.errors.append(
                LokasiImportError(row_num, 'id maksimal 2 karakter.')
            )
            continue
        if lokasi_id in seen_in_file:
            result.errors.append(
                LokasiImportError(
                    row_num,
                    f'id "{lokasi_id}" duplikat di file CSV.',
                )
            )
            continue
        if lokasi_id in existing_ids:
            result.errors.append(
                LokasiImportError(
                    row_num,
                    f'id "{lokasi_id}" sudah terdaftar.',
                )
            )
            continue
        seen_in_file.add(lokasi_id)

        if not nama:
            result.errors.append(
                LokasiImportError(row_num, 'Kolom nama wajib diisi.')
            )
            continue
        if len(nama) > 128:
            result.errors.append(
                LokasiImportError(row_num, 'Nama maksimal 128 karakter.')
            )
            continue

        to_create.append(Lokasi(id=lokasi_id, nama=nama))

    if result.errors:
        return result

    if not to_create:
        result.errors.append(
            LokasiImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    with transaction.atomic():
        Lokasi.objects.bulk_create(to_create)
    result.created = len(to_create)
    return result
