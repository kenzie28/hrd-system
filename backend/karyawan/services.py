from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from django.contrib.auth.models import User
from django.db import transaction

from core.models import Lokasi

from .models import Karyawan

DEFAULT_PORTAL_PASSWORD = '123'

COL_KARYAWAN_ID = 'karyawan_id'
COL_NAMA = 'nama'
COL_LEVEL = 'level'
COL_JABATAN = 'jabatan'
COL_WILAYAH = 'wilayah'
COL_LOKASI = 'lokasi_kerja'
REQUIRED_COLUMNS = [COL_KARYAWAN_ID, COL_NAMA, COL_LEVEL]


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
    errors: list[KaryawanImportError] = field(default_factory=list)
    received_headers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_karyawan_import_result(result: KaryawanImportResult) -> dict:
    return {
        'ok': result.ok,
        'total_rows': result.total_rows,
        'created': result.created,
        'errors': [{'row': e.row, 'message': e.message} for e in result.errors],
        'received_headers': result.received_headers,
        'required_columns': REQUIRED_COLUMNS,
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


def import_karyawan_csv(upload) -> KaryawanImportResult:
    """Validate and create Karyawan rows from CSV.

    Required columns: karyawan_id, nama, level.
    Optional: jabatan, wilayah, lokasi_kerja (existing Lokasi PK).
    All rows are validated before any write.
    """
    result = KaryawanImportResult()

    try:
        raw = upload.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8-sig')
        else:
            text = str(raw)
    except UnicodeDecodeError:
        result.errors.append(
            KaryawanImportError(0, 'File harus berformat UTF-8.')
        )
        return result

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        result.errors.append(
            KaryawanImportError(0, 'File CSV kosong atau tidak memiliki header.')
        )
        return result

    headers = [h.strip() if h else '' for h in reader.fieldnames]
    result.received_headers = headers
    reader.fieldnames = headers
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
