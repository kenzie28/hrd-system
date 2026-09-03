from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from django.contrib.auth.models import User
from django.db import transaction

from lokasi.models import Lokasi

from .models import Karyawan

DEFAULT_PORTAL_PASSWORD = '123'

COL_KARYAWAN_ID = 'karyawan_id'
COL_NAMA = 'nama'
COL_LEVEL = 'level'
COL_JABATAN = 'jabatan'
COL_WILAYAH = 'wilayah'
COL_LOKASI = 'lokasi_kerja'
COL_CUTI = 'cuti_tahunan'
REQUIRED_COLUMNS = [COL_KARYAWAN_ID, COL_NAMA, COL_LEVEL]
OPTIONAL_COLUMNS = [COL_JABATAN, COL_WILAYAH, COL_LOKASI]
UPDATE_OPTIONAL_COLUMNS = [
    COL_NAMA,
    COL_LEVEL,
    COL_JABATAN,
    COL_WILAYAH,
    COL_LOKASI,
    COL_CUTI,
]


def create_portal_login(karyawan, password=DEFAULT_PORTAL_PASSWORD):
    """Create (or reset) the Django User used to log into the employee portal.

    The User's username mirrors the employee's 7-digit karyawan_id. The employee is
    flagged to change the password on first login.
    """
    user, _ = User.objects.get_or_create(username=karyawan.karyawan_id)
    user.set_password(password)
    user.save()
    karyawan.user = user
    karyawan.must_change_password = True
    karyawan.save(update_fields=['user', 'must_change_password'])
    return user


@dataclass
class KaryawanImportError:
    row: int
    message: str


@dataclass
class KaryawanImportResult:
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    errors: list[KaryawanImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)
    required_columns: list[str] = field(default_factory=lambda: list(REQUIRED_COLUMNS))
    optional_columns: list[str] = field(default_factory=lambda: list(OPTIONAL_COLUMNS))

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_karyawan_import_result(result: KaryawanImportResult) -> dict:
    return {
        'ok': result.ok,
        'total_rows': result.total_rows,
        'created': result.created,
        'updated': result.updated,
        'errors': [{'row': e.row, 'message': e.message} for e in result.errors],
        'received_headers': result.received_headers,
        'required_columns': result.required_columns,
        'optional_columns': result.optional_columns,
    }


def _detect_delimiter(text: str) -> str:
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


def _decode_upload(upload, result: KaryawanImportResult) -> str | None:
    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            return raw.decode('utf-8-sig')
        return str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            KaryawanImportError(0, 'File harus berformat UTF-8.')
        )
        return None


def _csv_reader(text: str, result: KaryawanImportResult) -> csv.DictReader | None:
    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            KaryawanImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return None

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
    return reader


def import_karyawan_csv(upload) -> KaryawanImportResult:
    """Validate and create Karyawan rows from CSV.

    Required columns: karyawan_id, nama, level.
    Optional: jabatan, wilayah, lokasi_kerja (existing Lokasi PK).
    All rows are validated before any write.
    """
    result = KaryawanImportResult()

    text = _decode_upload(upload, result)
    if text is None:
        return result

    reader = _csv_reader(text, result)
    if reader is None:
        return result

    headers = result.received_headers
    header_set = set(headers)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        result.errors.append(
            KaryawanImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    lokasi_cache: dict[str, Lokasi | None] = {}
    existing_ids = set(Karyawan.objects.values_list('karyawan_id', flat=True))
    seen_in_file: set[str] = set()
    to_create: list[Karyawan] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get(COL_KARYAWAN_ID) or '').strip()
        nama = (row.get(COL_NAMA) or '').strip()
        level_raw = (row.get(COL_LEVEL) or '').strip()
        jabatan = (row.get(COL_JABATAN) or '').strip() if COL_JABATAN in header_set else ''
        wilayah = (row.get(COL_WILAYAH) or '').strip() if COL_WILAYAH in header_set else ''
        lokasi_id = (row.get(COL_LOKASI) or '').strip() if COL_LOKASI in header_set else ''

        if not karyawan_id:
            result.errors.append(
                KaryawanImportError(row_num, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if len(karyawan_id) > 7:
            result.errors.append(
                KaryawanImportError(
                    row_num, 'karyawan_id maksimal 7 karakter.'
                )
            )
            continue
        if karyawan_id in seen_in_file:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" duplikat di file CSV.',
                )
            )
            continue
        if karyawan_id in existing_ids:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" sudah terdaftar.',
                )
            )
            continue
        seen_in_file.add(karyawan_id)

        if not nama:
            result.errors.append(
                KaryawanImportError(row_num, 'Kolom nama wajib diisi.')
            )
            continue
        if len(nama) > 128:
            result.errors.append(
                KaryawanImportError(row_num, 'Nama maksimal 128 karakter.')
            )
            continue

        if not level_raw:
            result.errors.append(
                KaryawanImportError(row_num, 'Kolom level wajib diisi.')
            )
            continue
        try:
            level = int(level_raw)
        except ValueError:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'level harus angka 1–8 (diterima: "{level_raw}").',
                )
            )
            continue
        if level < 1 or level > 8:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'level harus antara 1–8 (diterima: {level}).',
                )
            )
            continue

        if len(jabatan) > 128:
            result.errors.append(
                KaryawanImportError(row_num, 'jabatan maksimal 128 karakter.')
            )
            continue
        if len(wilayah) > 3:
            result.errors.append(
                KaryawanImportError(row_num, 'wilayah maksimal 3 karakter.')
            )
            continue

        lokasi = None
        if lokasi_id:
            if len(lokasi_id) > 2:
                result.errors.append(
                    KaryawanImportError(
                        row_num, 'lokasi_kerja maksimal 2 karakter.'
                    )
                )
                continue
            if lokasi_id not in lokasi_cache:
                lokasi_cache[lokasi_id] = Lokasi.objects.filter(
                    pk=lokasi_id
                ).first()
            lokasi = lokasi_cache[lokasi_id]
            if lokasi is None:
                result.errors.append(
                    KaryawanImportError(
                        row_num,
                        f'lokasi_kerja "{lokasi_id}" tidak ditemukan.',
                    )
                )
                continue

        to_create.append(
            Karyawan(
                karyawan_id=karyawan_id,
                nama=nama,
                level=level,
                jabatan=jabatan,
                wilayah=wilayah,
                lokasi_kerja=lokasi,
            )
        )

    if result.errors:
        return result

    if not to_create:
        result.errors.append(
            KaryawanImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    with transaction.atomic():
        for karyawan in to_create:
            karyawan.save()
    result.created = len(to_create)
    return result


def _parse_level(raw: str, row_num: int, result: KaryawanImportResult) -> int | None:
    try:
        level = int(raw)
    except ValueError:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'level harus angka 1–8 (diterima: "{raw}").',
            )
        )
        return None
    if level < 1 or level > 8:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'level harus antara 1–8 (diterima: {level}).',
            )
        )
        return None
    return level


def _parse_cuti_tahunan(
    raw: str, row_num: int, result: KaryawanImportResult
) -> int | None:
    try:
        cuti = int(raw)
    except ValueError:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'cuti_tahunan harus angka (diterima: "{raw}").',
            )
        )
        return None
    if cuti < 0 or cuti > 32767:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'cuti_tahunan harus antara 0–32767 (diterima: {cuti}).',
            )
        )
        return None
    return cuti


def _resolve_lokasi(
    lokasi_id: str,
    row_num: int,
    result: KaryawanImportResult,
    lokasi_cache: dict[str, Lokasi | None],
) -> Lokasi | None:
    """Return Lokasi or None. Appends an error and returns None when invalid.

    Callers must check ``result.errors`` for a new row error — empty
    ``lokasi_id`` is a valid clear (returns None without error).
    """
    if not lokasi_id:
        return None
    if len(lokasi_id) > 2:
        result.errors.append(
            KaryawanImportError(row_num, 'lokasi_kerja maksimal 2 karakter.')
        )
        return None
    if lokasi_id not in lokasi_cache:
        lokasi_cache[lokasi_id] = Lokasi.objects.filter(pk=lokasi_id).first()
    lokasi = lokasi_cache[lokasi_id]
    if lokasi is None:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'lokasi_kerja "{lokasi_id}" tidak ditemukan.',
            )
        )
    return lokasi


def import_karyawan_update_csv(upload) -> KaryawanImportResult:
    """Partial-update existing Karyawan rows from CSV.

    Required column: karyawan_id (must already exist).
    Any other recognized column present in the header is applied to every row
    — empty cells clear blankable fields (jabatan, wilayah, lokasi_kerja) and
    are rejected for nama, level, and cuti_tahunan.
    All rows are validated before any write.
    """
    result = KaryawanImportResult(
        required_columns=[COL_KARYAWAN_ID],
        optional_columns=list(UPDATE_OPTIONAL_COLUMNS),
    )

    text = _decode_upload(upload, result)
    if text is None:
        return result

    reader = _csv_reader(text, result)
    if reader is None:
        return result

    headers = result.received_headers
    header_set = set(headers)
    if COL_KARYAWAN_ID not in header_set:
        result.errors.append(
            KaryawanImportError(0, 'Kolom wajib tidak ditemukan: karyawan_id.')
        )
        return result

    empty_headers = [i + 1 for i, h in enumerate(headers) if not h]
    if empty_headers:
        result.errors.append(
            KaryawanImportError(0, 'File CSV memiliki header kosong.')
        )
        return result

    known = {COL_KARYAWAN_ID, *UPDATE_OPTIONAL_COLUMNS}
    unknown = [h for h in headers if h not in known]
    if unknown:
        result.errors.append(
            KaryawanImportError(
                0,
                'Kolom tidak dikenali: '
                + ', '.join(unknown)
                + '. Kolom yang boleh diisi: '
                + ', '.join(UPDATE_OPTIONAL_COLUMNS)
                + '.',
            )
        )
        return result

    update_columns = [c for c in UPDATE_OPTIONAL_COLUMNS if c in header_set]
    if not update_columns:
        result.errors.append(
            KaryawanImportError(
                0,
                'Tidak ada kolom yang diubah. Sertakan minimal satu kolom: '
                + ', '.join(UPDATE_OPTIONAL_COLUMNS)
                + '.',
            )
        )
        return result

    if len(headers) != len(set(headers)):
        result.errors.append(
            KaryawanImportError(0, 'File CSV memiliki nama kolom yang duplikat.')
        )
        return result

    lokasi_cache: dict[str, Lokasi | None] = {}
    seen_in_file: set[str] = set()
    pending: list[tuple[int, str, dict]] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get(COL_KARYAWAN_ID) or '').strip()
        row_had_error = False

        if not karyawan_id:
            result.errors.append(
                KaryawanImportError(row_num, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if len(karyawan_id) > 7:
            result.errors.append(
                KaryawanImportError(
                    row_num, 'karyawan_id maksimal 7 karakter.'
                )
            )
            continue
        if karyawan_id in seen_in_file:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" duplikat di file CSV.',
                )
            )
            continue
        seen_in_file.add(karyawan_id)

        fields: dict = {}

        if COL_NAMA in header_set:
            nama = (row.get(COL_NAMA) or '').strip()
            if not nama:
                result.errors.append(
                    KaryawanImportError(row_num, 'Kolom nama tidak boleh kosong.')
                )
                row_had_error = True
            elif len(nama) > 128:
                result.errors.append(
                    KaryawanImportError(row_num, 'Nama maksimal 128 karakter.')
                )
                row_had_error = True
            else:
                fields['nama'] = nama

        if COL_LEVEL in header_set:
            level_raw = (row.get(COL_LEVEL) or '').strip()
            if not level_raw:
                result.errors.append(
                    KaryawanImportError(row_num, 'Kolom level tidak boleh kosong.')
                )
                row_had_error = True
            else:
                level = _parse_level(level_raw, row_num, result)
                if level is None:
                    row_had_error = True
                else:
                    fields['level'] = level

        if COL_JABATAN in header_set:
            jabatan = (row.get(COL_JABATAN) or '').strip()
            if len(jabatan) > 128:
                result.errors.append(
                    KaryawanImportError(row_num, 'jabatan maksimal 128 karakter.')
                )
                row_had_error = True
            else:
                fields['jabatan'] = jabatan

        if COL_WILAYAH in header_set:
            wilayah = (row.get(COL_WILAYAH) or '').strip()
            if len(wilayah) > 3:
                result.errors.append(
                    KaryawanImportError(row_num, 'wilayah maksimal 3 karakter.')
                )
                row_had_error = True
            else:
                fields['wilayah'] = wilayah

        if COL_LOKASI in header_set:
            error_count = len(result.errors)
            lokasi_id = (row.get(COL_LOKASI) or '').strip()
            lokasi = _resolve_lokasi(lokasi_id, row_num, result, lokasi_cache)
            if len(result.errors) > error_count:
                row_had_error = True
            else:
                fields['lokasi_kerja'] = lokasi

        if COL_CUTI in header_set:
            cuti_raw = (row.get(COL_CUTI) or '').strip()
            if not cuti_raw:
                result.errors.append(
                    KaryawanImportError(
                        row_num, 'Kolom cuti_tahunan tidak boleh kosong.'
                    )
                )
                row_had_error = True
            else:
                cuti = _parse_cuti_tahunan(cuti_raw, row_num, result)
                if cuti is None:
                    row_had_error = True
                else:
                    fields['cuti_tahunan'] = cuti

        if row_had_error:
            continue
        pending.append((row_num, karyawan_id, fields))

    if result.errors:
        return result

    if not pending:
        result.errors.append(
            KaryawanImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    ids = [kid for _, kid, _ in pending]
    found = {
        k.karyawan_id: k
        for k in Karyawan.objects.filter(karyawan_id__in=ids)
    }
    missing_rows = [
        (row_num, kid) for row_num, kid, _ in pending if kid not in found
    ]
    if missing_rows:
        for row_num, kid in missing_rows:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{kid}" tidak ditemukan.',
                )
            )
        return result

    to_update: list[Karyawan] = []
    for _, karyawan_id, fields in pending:
        karyawan = found[karyawan_id]
        for attr, value in fields.items():
            setattr(karyawan, attr, value)
        to_update.append(karyawan)

    with transaction.atomic():
        Karyawan.objects.bulk_update(to_update, update_columns)
    result.updated = len(to_update)
    return result
