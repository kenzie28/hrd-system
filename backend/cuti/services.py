"""Workflow helpers and CSV imports for the leave (cuti) lifecycle."""
import csv
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.db import transaction

from absensi.invalidation import enqueue_days, suppress_signal_invalidation
from karyawan.models import Karyawan

from .models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti


CUTI_IMPORT_REQUIRED_COLUMNS = ['karyawan_id', 'tanggal']


@dataclass
class CutiImportError:
    row: int
    message: str


@dataclass
class CutiImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[CutiImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class _CutiImportRow:
    row: int
    karyawan_id: str
    tanggal: date


def serialize_cuti_import_result(result: CutiImportResult) -> dict:
    return {
        'ok': result.ok,
        'total_rows': result.total_rows,
        'created': result.created,
        'errors': [{'row': error.row, 'message': error.message} for error in result.errors],
        'received_headers': result.received_headers,
        'required_columns': CUTI_IMPORT_REQUIRED_COLUMNS,
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


def import_cuti_csv(upload, tipe: str) -> CutiImportResult:
    """Create approved one-day annual or sick leave requests from CSV.

    Duplicate rows, and dates already registered for the same employee and
    leave type, are skipped. Annual leave consumes the employee's remaining
    annual quota. Validation is all-or-nothing.
    """
    if tipe not in (TipeCuti.TAHUNAN, TipeCuti.SAKIT):
        raise ValueError('Tipe import cuti tidak didukung.')

    result = CutiImportResult()
    try:
        raw = upload.read()
        text = raw.decode('utf-8-sig') if isinstance(raw, bytes) else str(raw)
    except UnicodeDecodeError:
        result.errors.append(CutiImportError(0, 'File harus berformat UTF-8.'))
        return result

    reader = csv.DictReader(
        io.StringIO(text),
        delimiter=_detect_import_delimiter(text),
    )
    if reader.fieldnames is None:
        result.errors.append(
            CutiImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [header.strip() if header else '' for header in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    missing = [column for column in CUTI_IMPORT_REQUIRED_COLUMNS if column not in headers]
    if missing:
        result.errors.append(
            CutiImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    rows: list[_CutiImportRow] = []
    seen: set[tuple[str, date]] = set()
    karyawan_cache: dict[str, bool] = {}
    for row_number, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get('karyawan_id') or '').strip()
        tanggal_raw = (row.get('tanggal') or '').strip()

        if not karyawan_id:
            result.errors.append(
                CutiImportError(row_number, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if karyawan_id not in karyawan_cache:
            karyawan_cache[karyawan_id] = Karyawan.objects.filter(
                pk=karyawan_id
            ).exists()
        if not karyawan_cache[karyawan_id]:
            result.errors.append(
                CutiImportError(
                    row_number,
                    f'karyawan_id "{karyawan_id}" tidak ditemukan.',
                )
            )
            continue

        tanggal = _parse_import_date(tanggal_raw)
        if tanggal is None:
            result.errors.append(
                CutiImportError(
                    row_number,
                    f'tanggal harus format yyyy-mm-dd (diterima: "{tanggal_raw}").',
                )
            )
            continue

        key = (karyawan_id, tanggal)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_CutiImportRow(row_number, karyawan_id, tanggal))

    if result.errors:
        return result
    if result.total_rows == 0:
        result.errors.append(CutiImportError(0, 'File CSV tidak memiliki baris data.'))
        return result

    with transaction.atomic():
        employees = {
            employee.pk: employee
            for employee in Karyawan.objects.select_for_update()
            .filter(pk__in={row.karyawan_id for row in rows})
            .order_by('pk')
        }
        existing = {
            (day.permohonan.karyawan_id, day.tanggal)
            for day in Cuti.objects.select_related('permohonan').filter(
                permohonan__karyawan_id__in=employees,
                permohonan__tipe=tipe,
                permohonan__status=StatusPermohonanCuti.APPROVED,
                tanggal__in={row.tanggal for row in rows},
            )
        }
        to_create = [
            row for row in rows if (row.karyawan_id, row.tanggal) not in existing
        ]

        if tipe == TipeCuti.TAHUNAN:
            requested = Counter(row.karyawan_id for row in to_create)
            for karyawan_id, count in requested.items():
                employee = employees[karyawan_id]
                if count > employee.cuti_tahunan:
                    first_row = next(
                        row.row for row in to_create if row.karyawan_id == karyawan_id
                    )
                    result.errors.append(
                        CutiImportError(
                            first_row,
                            f'Jatah cuti tahunan karyawan_id "{karyawan_id}" tidak cukup '
                            f'(tersisa {employee.cuti_tahunan}, dibutuhkan {count}).',
                        )
                    )
            if result.errors:
                return result

        for row in to_create:
            request = PermohonanCuti.objects.create(
                karyawan=employees[row.karyawan_id],
                tipe=tipe,
                tanggal_mulai=row.tanggal,
                tanggal_selesai=row.tanggal,
                status=StatusPermohonanCuti.APPROVED,
                supervisor=None,
                hrd_approver=None,
            )
            Cuti.objects.create(permohonan=request, tanggal=row.tanggal)

        if tipe == TipeCuti.TAHUNAN:
            for karyawan_id, count in Counter(
                row.karyawan_id for row in to_create
            ).items():
                employee = employees[karyawan_id]
                employee.cuti_tahunan -= count
                employee.save(update_fields=['cuti_tahunan'])

        result.created = len(to_create)

    return result


@transaction.atomic
def approve_by_hrd(permohonan: PermohonanCuti, hrd_approver) -> int:
    """Finalize a request that HRD approved and materialize the per-day Cuti rows.

    Returns the number of Cuti (day) rows created. Idempotent per request: any
    existing day rows for the request are cleared first.
    """
    was_approved_before = permohonan.status == StatusPermohonanCuti.APPROVED

    old_days = list(permohonan.hari_cuti.values_list('tanggal', flat=True))

    rows = []
    current = permohonan.tanggal_mulai
    while current <= permohonan.tanggal_selesai:
        rows.append(Cuti(permohonan=permohonan, tanggal=current))
        current += timedelta(days=1)

    with suppress_signal_invalidation():
        permohonan.status = StatusPermohonanCuti.APPROVED
        permohonan.hrd_approver = hrd_approver
        permohonan.save(update_fields=['status', 'hrd_approver'])
        permohonan.hari_cuti.all().delete()
        Cuti.objects.bulk_create(rows)
    enqueue_days(
        (permohonan.karyawan_id, day)
        for day in {*old_days, *(row.tanggal for row in rows)}
    )

    if permohonan.tipe == TipeCuti.TAHUNAN and not was_approved_before:
        karyawan = permohonan.karyawan
        karyawan.cuti_tahunan = max(0, karyawan.cuti_tahunan - len(rows))
        karyawan.save(update_fields=['cuti_tahunan'])

    return len(rows)


def _jumlah_hari(permohonan: PermohonanCuti) -> int:
    return (permohonan.tanggal_selesai - permohonan.tanggal_mulai).days + 1


@transaction.atomic
def approve_cancellation_by_hrd(permohonan: PermohonanCuti) -> int:
    """Finalize post-approval cancellation: drop day rows and restore quota.

    Returns the number of Cuti (day) rows removed. ``cuti_tahunan`` is restored
    only for Cuti Tahunan, using the day-row count (falling back to the
    inclusive date range if rows were already gone).
    """
    old_days = list(permohonan.hari_cuti.values_list('tanggal', flat=True))
    day_count = len(old_days)
    if day_count == 0:
        day_count = _jumlah_hari(permohonan)

    with suppress_signal_invalidation():
        permohonan.hari_cuti.all().delete()

        if permohonan.tipe == TipeCuti.TAHUNAN:
            karyawan = permohonan.karyawan
            karyawan.cuti_tahunan += day_count
            karyawan.save(update_fields=['cuti_tahunan'])

        permohonan.status = StatusPermohonanCuti.DIBATALKAN
        permohonan.save(update_fields=['status'])
    enqueue_days(
        ((permohonan.karyawan_id, day) for day in old_days)
    )

    return day_count
