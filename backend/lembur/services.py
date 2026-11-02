"""Workflow helpers and CSV import for the overtime (lembur) request lifecycle."""
import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

from django.db import transaction

from karyawan.models import Karyawan

from .models import PermohonanLembur, StatusPermohonanLembur


LEMBUR_IMPORT_REQUIRED_COLUMNS = ['karyawan_id', 'tanggal']


@dataclass
class LemburImportError:
    row: int
    message: str


@dataclass
class LemburImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[LemburImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class _LemburImportRow:
    row: int
    karyawan_id: str
    tanggal: date


def serialize_lembur_import_result(result: LemburImportResult) -> dict:
    return {
        'ok': result.ok,
        'total_rows': result.total_rows,
        'created': result.created,
        'errors': [{'row': error.row, 'message': error.message} for error in result.errors],
        'received_headers': result.received_headers,
        'required_columns': LEMBUR_IMPORT_REQUIRED_COLUMNS,
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


def import_lembur_csv(upload) -> LemburImportResult:
    """Create approved one-day overtime requests from CSV.

    Duplicate rows, and dates that already have an approved request for the
    same employee, are skipped. Validation is all-or-nothing.
    """
    result = LemburImportResult()
    try:
        raw = upload.read()
        text = raw.decode('utf-8-sig') if isinstance(raw, bytes) else str(raw)
    except UnicodeDecodeError:
        result.errors.append(LemburImportError(0, 'File harus berformat UTF-8.'))
        return result

    reader = csv.DictReader(
        io.StringIO(text),
        delimiter=_detect_import_delimiter(text),
    )
    if reader.fieldnames is None:
        result.errors.append(
            LemburImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [header.strip() if header else '' for header in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    missing = [
        column for column in LEMBUR_IMPORT_REQUIRED_COLUMNS if column not in headers
    ]
    if missing:
        result.errors.append(
            LemburImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    rows: list[_LemburImportRow] = []
    seen: set[tuple[str, date]] = set()
    karyawan_cache: dict[str, bool] = {}
    for row_number, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get('karyawan_id') or '').strip()
        tanggal_raw = (row.get('tanggal') or '').strip()

        if not karyawan_id:
            result.errors.append(
                LemburImportError(row_number, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if karyawan_id not in karyawan_cache:
            karyawan_cache[karyawan_id] = Karyawan.objects.filter(
                pk=karyawan_id
            ).exists()
        if not karyawan_cache[karyawan_id]:
            result.errors.append(
                LemburImportError(
                    row_number,
                    f'karyawan_id "{karyawan_id}" tidak ditemukan.',
                )
            )
            continue

        tanggal = _parse_import_date(tanggal_raw)
        if tanggal is None:
            result.errors.append(
                LemburImportError(
                    row_number,
                    f'tanggal harus format yyyy-mm-dd (diterima: "{tanggal_raw}").',
                )
            )
            continue

        key = (karyawan_id, tanggal)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_LemburImportRow(row_number, karyawan_id, tanggal))

    if result.errors:
        return result
    if result.total_rows == 0:
        result.errors.append(LemburImportError(0, 'File CSV tidak memiliki baris data.'))
        return result

    with transaction.atomic():
        employees = {
            employee.pk: employee
            for employee in Karyawan.objects.select_for_update()
            .filter(pk__in={row.karyawan_id for row in rows})
            .order_by('pk')
        }
        existing = set(
            PermohonanLembur.objects.filter(
                karyawan_id__in=employees,
                status=StatusPermohonanLembur.APPROVED,
                tanggal__in={row.tanggal for row in rows},
            ).values_list('karyawan_id', 'tanggal')
        )
        to_create = [
            row for row in rows if (row.karyawan_id, row.tanggal) not in existing
        ]

        for row in to_create:
            create_approved_lembur(employees[row.karyawan_id], row.tanggal)

        result.created = len(to_create)

    return result


def create_approved_lembur(karyawan, tanggal) -> PermohonanLembur:
    """Create one already-approved overtime request for a single day."""
    return PermohonanLembur.objects.create(
        karyawan=karyawan,
        tanggal=tanggal,
        alasan='',
        status=StatusPermohonanLembur.APPROVED,
        supervisor=None,
        hrd_approver=None,
    )


@transaction.atomic
def ensure_approved_lembur(karyawan, tanggal) -> tuple[PermohonanLembur, bool]:
    """Return the approved request for this day, creating it when missing."""
    existing = (
        PermohonanLembur.objects.select_for_update()
        .filter(
            karyawan=karyawan,
            tanggal=tanggal,
            status=StatusPermohonanLembur.APPROVED,
        )
        .order_by('pk')
        .first()
    )
    if existing is not None:
        return existing, False
    return create_approved_lembur(karyawan, tanggal), True


@transaction.atomic
def clear_approved_lembur(karyawan, tanggal) -> int:
    """Delete approved overtime for this day. Other statuses are left in place."""
    rows = list(
        PermohonanLembur.objects.select_for_update().filter(
            karyawan=karyawan,
            tanggal=tanggal,
            status=StatusPermohonanLembur.APPROVED,
        )
    )
    for row in rows:
        row.delete()
    return len(rows)


@transaction.atomic
def approve_by_hrd(permohonan: PermohonanLembur, hrd_approver) -> None:
    """Finalize a request that HRD approved."""
    permohonan.status = StatusPermohonanLembur.APPROVED
    permohonan.hrd_approver = hrd_approver
    permohonan.save(update_fields=['status', 'hrd_approver'])
