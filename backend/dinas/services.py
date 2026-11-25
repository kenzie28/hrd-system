"""CSV import and date-range assignment for dinas days."""
import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.db import transaction

from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur

from .models import Dinas


# One assignment per calendar day. A year is enough for a single admin action.
MAX_DINAS_RANGE_DAYS = 366

DINAS_IMPORT_REQUIRED_COLUMNS = ['karyawan_id', 'tanggal']


class DinasRangeError(Exception):
    """The requested dinas date range cannot be created."""


@dataclass
class DinasImportError:
    row: int
    message: str


@dataclass
class DinasImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[DinasImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class _DinasImportRow:
    row: int
    karyawan_id: str
    tanggal: date


def serialize_dinas_import_result(result: DinasImportResult) -> dict:
    return {
        'ok': result.ok,
        'total_rows': result.total_rows,
        'created': result.created,
        'errors': [{'row': error.row, 'message': error.message} for error in result.errors],
        'received_headers': result.received_headers,
        'required_columns': DINAS_IMPORT_REQUIRED_COLUMNS,
    }


def _detect_import_delimiter(text: str) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), '')
    if not first_line:
        return ','
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=',;')
        if dialect.delimiter in (',', ';'):
            return dialect.delimiter
    except csv.Error:
        pass
    return ';' if first_line.count(';') > first_line.count(',') else ','


def _parse_import_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date()
    except (AttributeError, ValueError):
        return None


def _occupied_days(karyawan_ids, dates) -> set[tuple[str, date]]:
    """Days that already have dinas or approved lembur."""
    occupied = set(
        Dinas.objects.filter(
            karyawan_id__in=karyawan_ids,
            tanggal__in=dates,
        ).values_list('karyawan_id', 'tanggal')
    )
    occupied.update(
        PermohonanLembur.objects.filter(
            karyawan_id__in=karyawan_ids,
            status=StatusPermohonanLembur.APPROVED,
            tanggal__in=dates,
        ).values_list('karyawan_id', 'tanggal')
    )
    return occupied


def import_dinas_csv(upload) -> DinasImportResult:
    """Create dinas days from CSV.

    Duplicate rows, and dates that already have dinas or approved lembur for
    the same employee, are skipped. Validation is all-or-nothing.
    """
    result = DinasImportResult()
    try:
        raw = upload.read()
        text = raw.decode('utf-8-sig') if isinstance(raw, bytes) else str(raw)
    except UnicodeDecodeError:
        result.errors.append(DinasImportError(0, 'File harus berformat UTF-8.'))
        return result

    reader = csv.DictReader(
        io.StringIO(text),
        delimiter=_detect_import_delimiter(text),
    )
    if reader.fieldnames is None:
        result.errors.append(
            DinasImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [header.strip() if header else '' for header in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    missing = [
        column for column in DINAS_IMPORT_REQUIRED_COLUMNS if column not in headers
    ]
    if missing:
        result.errors.append(
            DinasImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    rows: list[_DinasImportRow] = []
    seen: set[tuple[str, date]] = set()
    karyawan_cache: dict[str, bool] = {}
    for row_number, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get('karyawan_id') or '').strip()
        tanggal_raw = (row.get('tanggal') or '').strip()

        if not karyawan_id:
            result.errors.append(
                DinasImportError(row_number, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if karyawan_id not in karyawan_cache:
            karyawan_cache[karyawan_id] = Karyawan.objects.filter(
                pk=karyawan_id
            ).exists()
        if not karyawan_cache[karyawan_id]:
            result.errors.append(
                DinasImportError(
                    row_number,
                    f'karyawan_id "{karyawan_id}" tidak ditemukan.',
                )
            )
            continue

        tanggal = _parse_import_date(tanggal_raw)
        if tanggal is None:
            result.errors.append(
                DinasImportError(
                    row_number,
                    f'tanggal harus format yyyy-mm-dd (diterima: "{tanggal_raw}").',
                )
            )
            continue

        key = (karyawan_id, tanggal)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_DinasImportRow(row_number, karyawan_id, tanggal))

    if result.errors:
        return result
    if result.total_rows == 0:
        result.errors.append(DinasImportError(0, 'File CSV tidak memiliki baris data.'))
        return result

    with transaction.atomic():
        employees = {
            employee.pk: employee
            for employee in Karyawan.objects.select_for_update()
            .filter(pk__in={row.karyawan_id for row in rows})
            .order_by('pk')
        }
        occupied = _occupied_days(employees, {row.tanggal for row in rows})
        to_create = [
            Dinas(karyawan=employees[row.karyawan_id], tanggal=row.tanggal)
            for row in rows
            if (row.karyawan_id, row.tanggal) not in occupied
        ]
        Dinas.objects.bulk_create(to_create)
        result.created = len(to_create)

    return result


@transaction.atomic
def create_dinas_range(karyawan, start: date, end: date) -> tuple[int, int]:
    """Create dinas for each day in ``[start, end]``.

    A day that already has dinas or approved lembur is left as-is.
    Returns ``(created, skipped)``.
    """
    if end < start:
        raise DinasRangeError('tanggal_selesai harus pada atau setelah tanggal_mulai.')
    span = (end - start).days + 1
    if span > MAX_DINAS_RANGE_DAYS:
        raise DinasRangeError(
            f'Rentang maksimal {MAX_DINAS_RANGE_DAYS} hari (diterima: {span}).'
        )

    locked = Karyawan.objects.select_for_update().filter(pk=karyawan.pk).first()
    if locked is None:
        raise DinasRangeError('Karyawan tidak ditemukan.')

    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    occupied = {tanggal for _karyawan_id, tanggal in _occupied_days([locked.pk], dates)}
    to_create = [
        Dinas(karyawan=locked, tanggal=tanggal)
        for tanggal in dates
        if tanggal not in occupied
    ]
    Dinas.objects.bulk_create(to_create)
    return len(to_create), span - len(to_create)
