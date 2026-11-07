"""CSV import for Koreksi (karyawan_id, tipe, nominal, bulan)."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from django.db import transaction

from karyawan.models import Karyawan

from .models import Koreksi, TipeKoreksi

COL_KARYAWAN_ID = 'karyawan_id'
COL_TIPE = 'tipe'
COL_NOMINAL = 'nominal'
COL_BULAN = 'bulan'
REQUIRED_COLUMNS = [COL_KARYAWAN_ID, COL_TIPE, COL_NOMINAL, COL_BULAN]

TIPE_BY_LABEL = {
    TipeKoreksi.ADMIN.label: TipeKoreksi.ADMIN,
    TipeKoreksi.ABSENSI.label: TipeKoreksi.ABSENSI,
}

_NOMINAL_RE = re.compile(r'^-?\d+$')
_BIGINT_MIN = -1 << 63
_BIGINT_MAX = (1 << 63) - 1


@dataclass
class KoreksiImportError:
    row: int
    message: str


@dataclass
class KoreksiImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[KoreksiImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_koreksi_import_result(result: KoreksiImportResult) -> dict:
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


def _strip_quote(value: str) -> str:
    """Strip surrounding space and a leading Excel-text ``'`` marker."""
    value = (value or '').strip()
    return value[1:].strip() if value.startswith("'") else value


def _format_karyawan_id(value: str) -> str:
    return _strip_quote(value).zfill(7)[-7:]


def _parse_nominal(value: str) -> tuple[int | None, str | None]:
    raw = _strip_quote(value)
    if not raw:
        return None, 'Kolom nominal wajib diisi.'
    if not _NOMINAL_RE.fullmatch(raw):
        return None, f'Nominal tidak valid: {raw!r}.'
    number = int(raw)
    if number < _BIGINT_MIN or number > _BIGINT_MAX:
        return None, f'Nominal di luar batas bilangan bulat: {raw}.'
    return number, None


def _parse_bulan(value: str) -> date | None:
    raw = _strip_quote(value)
    if len(raw) == 6 and raw.isdigit():
        year, month = int(raw[:4]), int(raw[4:])
        if 1 <= month <= 12 and year >= 1:
            return date(year, month, 1)
        return None
    if len(raw) == 7 and raw[4] == '-':
        year_s, month_s = raw.split('-', 1)
        if (
            len(year_s) == 4
            and len(month_s) == 2
            and year_s.isdigit()
            and month_s.isdigit()
        ):
            year, month = int(year_s), int(month_s)
            if 1 <= month <= 12 and year >= 1:
                return date(year, month, 1)
        return None
    try:
        parsed = datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return None
    if parsed.year < 1:
        return None
    return date(parsed.year, parsed.month, 1)


def import_koreksi_csv(upload) -> KoreksiImportResult:
    """Validate and insert Koreksi rows from a CSV.

    Columns: karyawan_id, tipe, nominal, bulan. Delimiter may be comma or
    semicolon. Every row is inserted, including repeats of an existing
    karyawan, tipe, and month. All rows are validated before any write.
    On validation errors nothing is persisted.
    """
    result = KoreksiImportResult()

    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8-sig')
        else:
            text = str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            KoreksiImportError(0, 'File harus berformat UTF-8.')
        )
        return result

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            KoreksiImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    header_set = set(headers)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        result.errors.append(
            KoreksiImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    existing_ids = set(Karyawan.objects.values_list('karyawan_id', flat=True))
    to_create: list[Koreksi] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_raw = _strip_quote(row.get(COL_KARYAWAN_ID) or '')
        if not karyawan_raw:
            result.errors.append(
                KoreksiImportError(row_num, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        karyawan_id = _format_karyawan_id(karyawan_raw)
        if karyawan_id not in existing_ids:
            result.errors.append(
                KoreksiImportError(
                    row_num,
                    f'Karyawan {karyawan_id} tidak ditemukan.',
                )
            )
            continue

        tipe_label = _strip_quote(row.get(COL_TIPE) or '')
        tipe = TIPE_BY_LABEL.get(tipe_label)
        if tipe is None:
            result.errors.append(
                KoreksiImportError(
                    row_num,
                    'Tipe harus Koreksi Admin atau Koreksi Absensi.',
                )
            )
            continue

        nominal, nominal_error = _parse_nominal(row.get(COL_NOMINAL) or '')
        if nominal_error:
            result.errors.append(KoreksiImportError(row_num, nominal_error))
            continue

        bulan_raw = _strip_quote(row.get(COL_BULAN) or '')
        if not bulan_raw:
            result.errors.append(
                KoreksiImportError(row_num, 'Kolom bulan wajib diisi.')
            )
            continue
        bulan = _parse_bulan(bulan_raw)
        if bulan is None:
            result.errors.append(
                KoreksiImportError(
                    row_num,
                    f'Bulan tidak valid: {bulan_raw!r}.',
                )
            )
            continue

        to_create.append(
            Koreksi(
                karyawan_id=karyawan_id,
                tipe=tipe,
                nominal=nominal,
                bulan=bulan,
            )
        )

    if result.errors:
        return result

    if not to_create:
        result.errors.append(
            KoreksiImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    with transaction.atomic():
        Koreksi.objects.bulk_create(to_create)
    result.created = len(to_create)
    return result
