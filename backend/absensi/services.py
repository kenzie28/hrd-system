"""CSV import for Absensi (karyawan_id, lokasi_kerja, tanggal, jam_masuk, jam_keluar)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.db import transaction

from core.models import Lokasi
from karyawan.models import Karyawan

from .models import Absensi

COL_KARYAWAN_ID = 'karyawan_id'
COL_LOKASI = 'lokasi_kerja'
COL_TANGGAL = 'tanggal'
COL_JAM_MASUK = 'jam_masuk'
COL_JAM_KELUAR = 'jam_keluar'
REQUIRED_COLUMNS = [COL_KARYAWAN_ID, COL_LOKASI, COL_TANGGAL, COL_JAM_MASUK, COL_JAM_KELUAR]


@dataclass
class AbsensiImportError:
    row: int
    message: str


@dataclass
class AbsensiImportResult:
    total_rows: int = 0
    created: int = 0
    errors: list[AbsensiImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_absensi_import_result(result: AbsensiImportResult) -> dict:
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


def _parse_tanggal(value: str) -> date | None:
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


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


def import_absensi_csv(upload) -> AbsensiImportResult:
    """Validate and create Absensi rows from a CSV with columns
    karyawan_id, lokasi_kerja, tanggal, jam_masuk, jam_keluar.

    karyawan_id must reference an existing Karyawan (by its business ID, not
    the numeric PK). lokasi_kerja must reference an existing Lokasi. tanggal
    accepts yyyy-mm-dd; jam_masuk/jam_keluar accept HH:MM or HH:MM:SS. When
    jam_keluar is not after jam_masuk it is treated as an overnight shift
    (durasi spans into the next calendar day). Multiple rows for the same
    employee/day are allowed on purpose — HRD resolves conflicts separately.
    Delimiter may be comma or semicolon (auto-detected). All rows are
    validated before any write.
    """
    result = AbsensiImportResult()

    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8-sig')
        else:
            text = str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            AbsensiImportError(0, 'File harus berformat UTF-8.')
        )
        return result

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            AbsensiImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    header_set = set(headers)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        result.errors.append(
            AbsensiImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    karyawan_cache: dict[str, Karyawan | None] = {}
    lokasi_cache: dict[str, Lokasi | None] = {}
    to_create: list[Absensi] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get(COL_KARYAWAN_ID) or '').strip()
        lokasi_id = (row.get(COL_LOKASI) or '').strip()
        tanggal_raw = (row.get(COL_TANGGAL) or '').strip()
        jam_masuk_raw = (row.get(COL_JAM_MASUK) or '').strip()
        jam_keluar_raw = (row.get(COL_JAM_KELUAR) or '').strip()

        if not karyawan_id:
            result.errors.append(
                AbsensiImportError(row_num, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if karyawan_id not in karyawan_cache:
            karyawan_cache[karyawan_id] = Karyawan.objects.filter(
                karyawan_id=karyawan_id
            ).first()
        karyawan = karyawan_cache[karyawan_id]
        if karyawan is None:
            result.errors.append(
                AbsensiImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" tidak ditemukan.',
                )
            )
            continue

        if not lokasi_id:
            result.errors.append(
                AbsensiImportError(row_num, 'Kolom lokasi_kerja wajib diisi.')
            )
            continue
        if lokasi_id not in lokasi_cache:
            lokasi_cache[lokasi_id] = Lokasi.objects.filter(pk=lokasi_id).first()
        lokasi = lokasi_cache[lokasi_id]
        if lokasi is None:
            result.errors.append(
                AbsensiImportError(
                    row_num,
                    f'lokasi_kerja "{lokasi_id}" tidak ditemukan.',
                )
            )
            continue

        tanggal = _parse_tanggal(tanggal_raw)
        if tanggal is None:
            result.errors.append(
                AbsensiImportError(
                    row_num,
                    f'tanggal harus format yyyy-mm-dd (diterima: "{tanggal_raw}").',
                )
            )
            continue

        jam_masuk = _parse_time(jam_masuk_raw)
        if jam_masuk is None:
            result.errors.append(
                AbsensiImportError(
                    row_num,
                    f'jam_masuk harus format HH:MM (diterima: "{jam_masuk_raw}").',
                )
            )
            continue

        jam_keluar = _parse_time(jam_keluar_raw)
        if jam_keluar is None:
            result.errors.append(
                AbsensiImportError(
                    row_num,
                    f'jam_keluar harus format HH:MM (diterima: "{jam_keluar_raw}").',
                )
            )
            continue

        masuk_dt = datetime.combine(tanggal, jam_masuk)
        keluar_dt = datetime.combine(tanggal, jam_keluar)
        if keluar_dt <= masuk_dt:
            keluar_dt += timedelta(days=1)
        durasi = keluar_dt - masuk_dt

        to_create.append(
            Absensi(
                karyawan=karyawan,
                lokasi=lokasi,
                tanggal=tanggal,
                jam_masuk=jam_masuk,
                durasi=durasi,
            )
        )

    if result.errors:
        return result

    if not to_create:
        result.errors.append(
            AbsensiImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    with transaction.atomic():
        Absensi.objects.bulk_create(to_create)
    result.created = len(to_create)
    return result
