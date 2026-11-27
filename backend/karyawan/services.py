from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

from django.contrib.auth.models import User
from django.db import transaction

from absensi.invalidation import enqueue_location_changes
from lokasi.models import Lokasi

from .models import JenisKelamin, Karyawan, StatusKTk

DEFAULT_PORTAL_PASSWORD = '123'

COL_KARYAWAN_ID = 'karyawan_id'
COL_NAMA = 'nama'
COL_LEVEL = 'level'
COL_JABATAN = 'jabatan'
COL_WILAYAH = 'wilayah'
COL_LOKASI = 'lokasi_kerja'
COL_CUTI = 'cuti_tahunan'
COL_STATUS_K_TK = 'status_k_tk'
COL_NPWP = 'npwp'
COL_NO_BPJS = 'no_bpjs'
COL_NO_KPJ = 'no_kpj'
COL_TANGGAL_LAHIR = 'tanggal_lahir'
REQUIRED_COLUMNS = [COL_KARYAWAN_ID, COL_NAMA, COL_LEVEL]
OPTIONAL_COLUMNS = [COL_JABATAN, COL_WILAYAH, COL_LOKASI]
UPDATE_OPTIONAL_COLUMNS = [
    COL_NAMA,
    COL_LEVEL,
    COL_JABATAN,
    COL_WILAYAH,
    COL_LOKASI,
    COL_CUTI,
    COL_STATUS_K_TK,
    COL_NPWP,
    COL_NO_BPJS,
    COL_NO_KPJ,
    COL_TANGGAL_LAHIR,
]
_UPDATE_TEXT_LIMITS = {
    COL_NPWP: 20,
    COL_NO_BPJS: 16,
    COL_NO_KPJ: 16,
}
_STATUS_K_TK_VALUES = frozenset(StatusKTk.values)


KARYAWAN_EXPORT_COLUMNS = [
    COL_KARYAWAN_ID,
    COL_NAMA,
    COL_LEVEL,
    COL_JABATAN,
    COL_WILAYAH,
    COL_LOKASI,
    COL_CUTI,
    COL_STATUS_K_TK,
    COL_NPWP,
    COL_NO_BPJS,
    COL_NO_KPJ,
]


def export_karyawan_csv() -> str:
    """Serialize every Karyawan row as a flat CSV the update importer accepts."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(KARYAWAN_EXPORT_COLUMNS)
    for obj in Karyawan.objects.order_by('karyawan_id'):
        writer.writerow(
            [
                obj.karyawan_id,
                obj.nama,
                obj.level,
                obj.jabatan,
                obj.wilayah,
                obj.lokasi_kerja_id or '',
                obj.cuti_tahunan,
                obj.status_k_tk,
                obj.npwp,
                obj.no_bpjs,
                obj.no_kpj,
            ]
        )
    return buf.getvalue()


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
                    f'level harus angka 0–9 (diterima: "{level_raw}").',
                )
            )
            continue
        if level < 0 or level > 9:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'level harus antara 0–9 (diterima: {level}).',
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
                f'level harus angka 0–9 (diterima: "{raw}").',
            )
        )
        return None
    if level < 0 or level > 9:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'level harus antara 0–9 (diterima: {level}).',
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
    — empty cells clear blankable fields (jabatan, wilayah, lokasi_kerja,
    status_k_tk, npwp, no_bpjs, no_kpj, tanggal_lahir) and are rejected for
    nama, level, and cuti_tahunan.
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

        if COL_STATUS_K_TK in header_set:
            status_k_tk = (row.get(COL_STATUS_K_TK) or '').strip().upper()
            if status_k_tk and status_k_tk not in _STATUS_K_TK_VALUES:
                result.errors.append(
                    KaryawanImportError(
                        row_num,
                        'status_k_tk tidak valid: '
                        f'"{status_k_tk}". Pilihan: '
                        + ', '.join(StatusKTk.values)
                        + '.',
                    )
                )
                row_had_error = True
            else:
                fields['status_k_tk'] = status_k_tk

        for column, limit in _UPDATE_TEXT_LIMITS.items():
            if column not in header_set:
                continue
            value = (row.get(column) or '').strip()
            if len(value) > limit:
                result.errors.append(
                    KaryawanImportError(
                        row_num, f'{column} maksimal {limit} karakter.'
                    )
                )
                row_had_error = True
            else:
                fields[column] = value

        if COL_TANGGAL_LAHIR in header_set:
            ok, value = _parse_upsert_date(
                row.get(COL_TANGGAL_LAHIR) or '',
                row_num,
                COL_TANGGAL_LAHIR,
                result,
            )
            if ok:
                fields[COL_TANGGAL_LAHIR] = value
            else:
                row_had_error = True

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
    location_changes = []
    for _, karyawan_id, fields in pending:
        karyawan = found[karyawan_id]
        old_location_id = karyawan.lokasi_kerja_id
        for attr, value in fields.items():
            setattr(karyawan, attr, value)
        to_update.append(karyawan)
        location_changes.append(
            (karyawan_id, old_location_id, karyawan.lokasi_kerja_id)
        )

    with transaction.atomic():
        Karyawan.objects.bulk_update(to_update, update_columns)
        enqueue_location_changes(location_changes)
    result.updated = len(to_update)
    return result


UPSERT_REQUIRED_COLUMNS = [COL_KARYAWAN_ID, COL_NAMA, COL_LEVEL]
UPSERT_OPTIONAL_COLUMNS = [
    'nama_karyawan',
    'jabatan',
    'role',
    'status_kontrak',
    'percobaan_jabatan',
    'tanggal_kontrak_awal',
    'tanggal_kontrak_akhir',
    'tanggal_awal',
    'tanggal_lahir',
    'TG.LAHIR',
    'jenis_kelamin',
    'status_k_tk',
    'lokasi_kerja',
    'npwp',
    'no_bpjs',
    'no_kpj',
    'kpj',
    'tanggal_kpj',
]
_UPSERT_KNOWN_HEADERS = {
    'karyawan_id',
    'nama',
    'nama_karyawan',
    'level',
    'jabatan',
    'role',
    'status_kontrak',
    'percobaan_jabatan',
    'tanggal_kontrak_awal',
    'tanggal_kontrak_akhir',
    'tanggal_awal',
    'tanggal_lahir',
    'tg.lahir',
    'jenis_kelamin',
    'status_k_tk',
    'lokasi_kerja',
    'npwp',
    'no_bpjs',
    'no_kpj',
    'kpj',
    'tanggal_kpj',
}
_UPSERT_FIELD_HEADERS = {
    'nama': ('nama', 'nama_karyawan'),
    'level': ('level',),
    'jabatan': ('jabatan', 'role'),
    'status_kontrak': ('status_kontrak',),
    'percobaan_jabatan': ('percobaan_jabatan',),
    'tanggal_kontrak_awal': ('tanggal_kontrak_awal',),
    'tanggal_kontrak_akhir': ('tanggal_kontrak_akhir',),
    'tanggal_awal': ('tanggal_awal',),
    'tanggal_lahir': ('tanggal_lahir', 'tg.lahir'),
    'jenis_kelamin': ('jenis_kelamin',),
    'status_k_tk': ('status_k_tk',),
    'lokasi_kerja': ('lokasi_kerja',),
    'npwp': ('npwp',),
    'no_bpjs': ('no_bpjs',),
    'no_kpj': ('no_kpj', 'kpj'),
    'tanggal_kpj': ('tanggal_kpj',),
}
_UPSERT_DATE_FIELDS = frozenset(
    {
        'tanggal_kontrak_awal',
        'tanggal_kontrak_akhir',
        'tanggal_awal',
        'tanggal_lahir',
        'tanggal_kpj',
    }
)
_DATE_FORMATS = ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y')
_GENDER_VALUES = {
    'P': JenisKelamin.PEREMPUAN,
    'PEREMPUAN': JenisKelamin.PEREMPUAN,
    'L': JenisKelamin.LAKI_LAKI,
    'LAKI-LAKI': JenisKelamin.LAKI_LAKI,
    'LAKI LAKI': JenisKelamin.LAKI_LAKI,
}
_BOOL_TRUE = frozenset({'Y', 'YA', 'TRUE', '1'})
_BOOL_FALSE = frozenset({'N', 'TIDAK', 'FALSE', '0'})


def _header_key(header: str) -> str:
    return header.strip().lower()


def _upsert_header_map(headers: list[str], result: KaryawanImportResult) -> dict[str, str] | None:
    """Map a lowercased header to the original header, or record a header error."""
    lowered: dict[str, str] = {}
    for header in headers:
        key = _header_key(header)
        if not key:
            result.errors.append(
                KaryawanImportError(0, 'Header kosong tidak diperbolehkan.')
            )
            return None
        if key in lowered:
            result.errors.append(
                KaryawanImportError(0, f'Kolom duplikat: {header}.')
            )
            return None
        if key not in _UPSERT_KNOWN_HEADERS:
            result.errors.append(
                KaryawanImportError(0, f'Kolom tidak dikenal: {header}.')
            )
            return None
        lowered[key] = header
    return lowered


def _upsert_sources(lowered: dict[str, str]) -> dict[str, str]:
    """Model field -> original header. Canonical names win over aliases."""
    sources = {}
    for field_name, aliases in _UPSERT_FIELD_HEADERS.items():
        for alias in aliases:
            if alias in lowered:
                sources[field_name] = lowered[alias]
                break
    return sources


def _blank_date(text: str) -> bool:
    compact = text.replace(' ', '')
    return compact in {'', '-', '--'}


def _parse_upsert_date(raw: str, row_num: int, column: str, result: KaryawanImportResult):
    text = (raw or '').strip()
    if _blank_date(text):
        return True, None
    for fmt in _DATE_FORMATS:
        try:
            return True, datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    result.errors.append(
        KaryawanImportError(
            row_num,
            f'{column} bukan tanggal yang valid (diterima: "{text}").',
        )
    )
    return False, None


def _parse_upsert_gender(raw: str, row_num: int, result: KaryawanImportResult):
    text = (raw or '').strip()
    if not text:
        return True, ''
    gender = _GENDER_VALUES.get(text.upper())
    if gender is None:
        result.errors.append(
            KaryawanImportError(
                row_num,
                f'jenis_kelamin tidak valid: "{text}". Pilihan: P, L, Perempuan, Laki-Laki.',
            )
        )
        return False, ''
    return True, gender


def _parse_upsert_bool(raw: str, row_num: int, column: str, result: KaryawanImportResult):
    text = (raw or '').strip().upper()
    if not text or text in _BOOL_FALSE:
        return True, False
    if text in _BOOL_TRUE:
        return True, True
    result.errors.append(
        KaryawanImportError(
            row_num,
            f'{column} harus Y atau N (diterima: "{text}").',
        )
    )
    return False, False


def _apply_upsert_fields(karyawan: Karyawan, fields: dict) -> None:
    for attr, value in fields.items():
        if attr == 'lokasi_kerja':
            karyawan.lokasi_kerja_id = value
        else:
            setattr(karyawan, attr, value)


def import_karyawan_upsert_csv(upload) -> KaryawanImportResult:
    """Create or update Karyawan rows from the HO employee CSV.

    Existing rows are matched by karyawan_id. A lokasi code that is not in the
    database is created with the code as its name. Fields absent from the file,
    including wages, are left unchanged on update.
    Every row is validated before any write.
    """
    result = KaryawanImportResult(
        required_columns=list(UPSERT_REQUIRED_COLUMNS),
        optional_columns=list(UPSERT_OPTIONAL_COLUMNS),
    )
    text = _decode_upload(upload, result)
    if text is None:
        return result

    reader = _csv_reader(text, result)
    if reader is None:
        return result

    lowered = _upsert_header_map(result.received_headers, result)
    if lowered is None:
        return result

    missing = []
    if 'karyawan_id' not in lowered:
        missing.append(COL_KARYAWAN_ID)
    if 'nama' not in lowered and 'nama_karyawan' not in lowered:
        missing.append(COL_NAMA)
    if 'level' not in lowered:
        missing.append(COL_LEVEL)
    if missing:
        result.errors.append(
            KaryawanImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    sources = _upsert_sources(lowered)
    id_header = lowered['karyawan_id']
    seen_in_file: set[str] = set()
    pending: list[tuple[str, dict]] = []

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get(id_header) or '').strip()
        if not karyawan_id:
            result.errors.append(
                KaryawanImportError(row_num, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if len(karyawan_id) > 7:
            result.errors.append(
                KaryawanImportError(row_num, 'karyawan_id maksimal 7 karakter.')
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
        row_had_error = False
        for field_name, header in sources.items():
            raw = row.get(header) or ''
            if field_name == 'nama':
                nama = raw.strip()
                if not nama:
                    result.errors.append(
                        KaryawanImportError(row_num, 'Kolom nama wajib diisi.')
                    )
                    row_had_error = True
                elif len(nama) > 128:
                    result.errors.append(
                        KaryawanImportError(row_num, 'Nama maksimal 128 karakter.')
                    )
                    row_had_error = True
                else:
                    fields['nama'] = nama
            elif field_name == 'level':
                level_raw = raw.strip()
                if not level_raw:
                    result.errors.append(
                        KaryawanImportError(row_num, 'Kolom level wajib diisi.')
                    )
                    row_had_error = True
                else:
                    level = _parse_level(level_raw, row_num, result)
                    if level is None:
                        row_had_error = True
                    else:
                        fields['level'] = level
            elif field_name == 'jabatan':
                jabatan = raw.strip()
                if len(jabatan) > 128:
                    result.errors.append(
                        KaryawanImportError(row_num, 'jabatan maksimal 128 karakter.')
                    )
                    row_had_error = True
                else:
                    fields['jabatan'] = jabatan
            elif field_name == 'status_kontrak':
                status_kontrak = raw.strip()
                if len(status_kontrak) > 2:
                    result.errors.append(
                        KaryawanImportError(
                            row_num, 'status_kontrak maksimal 2 karakter.'
                        )
                    )
                    row_had_error = True
                else:
                    fields['status_kontrak'] = status_kontrak
            elif field_name == 'percobaan_jabatan':
                ok, value = _parse_upsert_bool(
                    raw, row_num, 'percobaan_jabatan', result
                )
                if ok:
                    fields['percobaan_jabatan'] = value
                else:
                    row_had_error = True
            elif field_name in _UPSERT_DATE_FIELDS:
                ok, value = _parse_upsert_date(raw, row_num, header, result)
                if ok:
                    fields[field_name] = value
                else:
                    row_had_error = True
            elif field_name == 'jenis_kelamin':
                ok, value = _parse_upsert_gender(raw, row_num, result)
                if ok:
                    fields['jenis_kelamin'] = value
                else:
                    row_had_error = True
            elif field_name == 'status_k_tk':
                status_k_tk = raw.strip().upper()
                if status_k_tk and status_k_tk not in _STATUS_K_TK_VALUES:
                    result.errors.append(
                        KaryawanImportError(
                            row_num,
                            'status_k_tk tidak valid: '
                            f'"{status_k_tk}". Pilihan: '
                            + ', '.join(StatusKTk.values)
                            + '.',
                        )
                    )
                    row_had_error = True
                else:
                    fields['status_k_tk'] = status_k_tk
            elif field_name == 'lokasi_kerja':
                lokasi_id = raw.strip()
                if len(lokasi_id) > 2:
                    result.errors.append(
                        KaryawanImportError(
                            row_num, 'lokasi_kerja maksimal 2 karakter.'
                        )
                    )
                    row_had_error = True
                else:
                    fields['lokasi_kerja'] = lokasi_id or None
            elif field_name == 'npwp':
                npwp = raw.strip()
                if len(npwp) > 20:
                    result.errors.append(
                        KaryawanImportError(row_num, 'npwp maksimal 20 karakter.')
                    )
                    row_had_error = True
                else:
                    fields['npwp'] = npwp
            elif field_name in ('no_bpjs', 'no_kpj'):
                number = raw.strip()
                if len(number) > 16:
                    result.errors.append(
                        KaryawanImportError(
                            row_num, f'{field_name} maksimal 16 karakter.'
                        )
                    )
                    row_had_error = True
                else:
                    fields[field_name] = number

        if row_had_error:
            continue
        pending.append((karyawan_id, fields))

    if result.errors:
        return result
    if not pending:
        result.errors.append(
            KaryawanImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    existing = {
        karyawan.karyawan_id: karyawan
        for karyawan in Karyawan.objects.filter(
            karyawan_id__in=[karyawan_id for karyawan_id, _ in pending]
        )
    }
    lokasi_codes = {
        fields['lokasi_kerja']
        for _, fields in pending
        if fields.get('lokasi_kerja')
    }
    update_fields = [
        'lokasi_kerja' if name == 'lokasi_kerja' else name for name in sources
    ]
    to_create: list[tuple[str, dict]] = []
    to_update: list[Karyawan] = []
    location_changes = []

    for karyawan_id, fields in pending:
        karyawan = existing.get(karyawan_id)
        if karyawan is None:
            to_create.append((karyawan_id, fields))
            continue
        old_location_id = karyawan.lokasi_kerja_id
        _apply_upsert_fields(karyawan, fields)
        to_update.append(karyawan)
        if 'lokasi_kerja' in fields:
            location_changes.append(
                (karyawan_id, old_location_id, karyawan.lokasi_kerja_id)
            )

    with transaction.atomic():
        for code in sorted(lokasi_codes):
            Lokasi.objects.get_or_create(id=code, defaults={'nama': code})
        for karyawan_id, fields in to_create:
            karyawan = Karyawan(karyawan_id=karyawan_id)
            _apply_upsert_fields(karyawan, fields)
            karyawan.save()
        if to_update:
            Karyawan.objects.bulk_update(to_update, update_fields)
            if location_changes:
                enqueue_location_changes(location_changes)

    result.created = len(to_create)
    result.updated = len(to_update)
    return result


COL_BASE_GAJI = 'base_gaji'
COL_GAJI_BULANAN = 'gaji_bulanan'
COL_TARGET_GAJI = 'target_gaji'
COL_BCA_TRANSFER = 'bca_transfer'
COL_ABSENSI_DIHITUNG = 'absensi_dihitung'
COL_LEMBUR_DIBAYAR = 'lembur_dibayar'
WAGE_UPDATE_OPTIONAL_COLUMNS = [
    COL_BASE_GAJI,
    COL_GAJI_BULANAN,
    COL_TARGET_GAJI,
    COL_BCA_TRANSFER,
    COL_ABSENSI_DIHITUNG,
    COL_LEMBUR_DIBAYAR,
]
_WAGE_UPDATE_NULLABLE = frozenset({COL_TARGET_GAJI, COL_BCA_TRANSFER})
_WAGE_UPDATE_AMOUNTS = frozenset({COL_BASE_GAJI, COL_GAJI_BULANAN})
_WAGE_UPDATE_BOOLEANS = frozenset({COL_ABSENSI_DIHITUNG, COL_LEMBUR_DIBAYAR})
_CSV_BOOL_TRUE = frozenset({'ya', 'true', 'yes', '1'})
_CSV_BOOL_FALSE = frozenset({'tidak', 'false', 'no', '0'})
_WAGE_MAX = (1 << 63) - 1


def _parse_non_negative_int(raw: str, column: str) -> tuple[int | None, str | None]:
    value = (raw or '').strip()
    if value.startswith("'"):
        value = value[1:].strip()
    if not value:
        return None, f'Kolom {column} wajib diisi.'
    if not value.isdigit():
        return None, f'{column} tidak valid: {raw.strip()!r}.'
    number = int(value)
    if number > _WAGE_MAX:
        return None, f'{column} di luar batas bilangan bulat: {value}.'
    return number, None


def _import_karyawan_amount_csv(upload, column: str) -> KaryawanImportResult:
    """Set one wage field from a CSV of karyawan_id,<column>.

    Each row updates that employee only. The whole file is validated before
    any write. An unknown or duplicate karyawan_id rejects the file.
    """
    required = [COL_KARYAWAN_ID, column]
    result = KaryawanImportResult(
        required_columns=list(required),
        optional_columns=[],
    )
    text = _decode_upload(upload, result)
    if text is None:
        return result

    reader = _csv_reader(text, result)
    if reader is None:
        return result

    header_set = set(reader.fieldnames or [])
    missing = [c for c in required if c not in header_set]
    if missing:
        result.errors.append(
            KaryawanImportError(
                0,
                f'Kolom wajib tidak ditemukan: {", ".join(missing)}.',
            )
        )
        return result

    seen: dict[str, int] = {}
    pending: list[tuple[int, str, int]] = []
    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        karyawan_id = (row.get(COL_KARYAWAN_ID) or '').strip()
        if not karyawan_id:
            result.errors.append(
                KaryawanImportError(row_num, 'Kolom karyawan_id wajib diisi.')
            )
            continue
        if len(karyawan_id) > 7:
            result.errors.append(
                KaryawanImportError(row_num, 'karyawan_id maksimal 7 karakter.')
            )
            continue
        if karyawan_id in seen:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" duplikat di file CSV (baris {seen[karyawan_id]}).',
                )
            )
            continue
        seen[karyawan_id] = row_num

        nominal, nominal_error = _parse_non_negative_int(row.get(column) or '', column)
        if nominal_error:
            result.errors.append(KaryawanImportError(row_num, nominal_error))
            continue
        pending.append((row_num, karyawan_id, nominal))

    if result.errors:
        return result
    if not pending:
        result.errors.append(
            KaryawanImportError(0, 'File CSV tidak memiliki baris data.')
        )
        return result

    found = {
        karyawan.karyawan_id: karyawan
        for karyawan in Karyawan.objects.filter(
            karyawan_id__in=[karyawan_id for _, karyawan_id, _ in pending]
        )
    }
    to_update: list[Karyawan] = []
    for row_num, karyawan_id, nominal in pending:
        karyawan = found.get(karyawan_id)
        if karyawan is None:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" tidak ditemukan.',
                )
            )
            continue
        setattr(karyawan, column, nominal)
        to_update.append(karyawan)

    if result.errors:
        return result

    with transaction.atomic():
        Karyawan.objects.bulk_update(to_update, [column])
    result.updated = len(to_update)
    return result


def import_base_gaji_csv(upload) -> KaryawanImportResult:
    """Set Karyawan.base_gaji from a CSV of karyawan_id,base_gaji."""
    return _import_karyawan_amount_csv(upload, COL_BASE_GAJI)


def import_gaji_bulanan_csv(upload) -> KaryawanImportResult:
    """Set Karyawan.gaji_bulanan from a CSV of karyawan_id,gaji_bulanan."""
    return _import_karyawan_amount_csv(upload, COL_GAJI_BULANAN)


def _parse_nullable_non_negative_int(raw: str, column: str) -> tuple[int | None, str | None]:
    """Empty clears the field. A present value must be a non-negative integer."""
    value = (raw or '').strip()
    if value.startswith("'"):
        value = value[1:].strip()
    if not value:
        return None, None
    if not value.isdigit():
        return None, f'{column} tidak valid: {raw.strip()!r}.'
    number = int(value)
    if number > _WAGE_MAX:
        return None, f'{column} di luar batas bilangan bulat: {value}.'
    return number, None


def _parse_csv_bool(raw: str, column: str) -> tuple[bool | None, str | None]:
    value = (raw or '').strip().lower()
    if not value:
        return None, f'Kolom {column} wajib diisi.'
    if value in _CSV_BOOL_TRUE:
        return True, None
    if value in _CSV_BOOL_FALSE:
        return False, None
    return None, f'{column} harus ya atau tidak.'


def import_gaji_karyawan_update_csv(upload) -> KaryawanImportResult:
    """Partial-update wage fields for existing karyawan.

    Required column: karyawan_id (must already exist).
    Any other recognized column present in the header is applied to every row.
    Empty cells clear target_gaji and bca_transfer. Empty cells are rejected
    for base_gaji, gaji_bulanan, absensi_dihitung, and lembur_dibayar.
    All rows are validated before any write.
    """
    result = KaryawanImportResult(
        required_columns=[COL_KARYAWAN_ID],
        optional_columns=list(WAGE_UPDATE_OPTIONAL_COLUMNS),
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

    empty_headers = [i + 1 for i, header in enumerate(headers) if not header]
    if empty_headers:
        result.errors.append(KaryawanImportError(0, 'File CSV memiliki header kosong.'))
        return result

    known = {COL_KARYAWAN_ID, *WAGE_UPDATE_OPTIONAL_COLUMNS}
    unknown = [header for header in headers if header not in known]
    if unknown:
        result.errors.append(
            KaryawanImportError(
                0,
                'Kolom tidak dikenali: '
                + ', '.join(unknown)
                + '. Kolom yang boleh diisi: '
                + ', '.join(WAGE_UPDATE_OPTIONAL_COLUMNS)
                + '.',
            )
        )
        return result

    update_columns = [column for column in WAGE_UPDATE_OPTIONAL_COLUMNS if column in header_set]
    if not update_columns:
        result.errors.append(
            KaryawanImportError(
                0,
                'Tidak ada kolom yang diubah. Sertakan minimal satu kolom: '
                + ', '.join(WAGE_UPDATE_OPTIONAL_COLUMNS)
                + '.',
            )
        )
        return result

    if len(headers) != len(set(headers)):
        result.errors.append(
            KaryawanImportError(0, 'File CSV memiliki nama kolom yang duplikat.')
        )
        return result

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
                KaryawanImportError(row_num, 'karyawan_id maksimal 7 karakter.')
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
        for column in update_columns:
            raw = row.get(column) or ''
            if column in _WAGE_UPDATE_NULLABLE:
                value, error = _parse_nullable_non_negative_int(raw, column)
            elif column in _WAGE_UPDATE_AMOUNTS:
                value, error = _parse_non_negative_int(raw, column)
            elif column in _WAGE_UPDATE_BOOLEANS:
                value, error = _parse_csv_bool(raw, column)
            else:
                value, error = None, f'Kolom tidak dikenal: {column}.'
            if error:
                result.errors.append(KaryawanImportError(row_num, error))
                row_had_error = True
            else:
                fields[column] = value

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

    ids = [karyawan_id for _, karyawan_id, _ in pending]
    found = {
        karyawan.karyawan_id: karyawan
        for karyawan in Karyawan.objects.filter(karyawan_id__in=ids)
    }
    missing_rows = [
        (row_num, karyawan_id)
        for row_num, karyawan_id, _ in pending
        if karyawan_id not in found
    ]
    if missing_rows:
        for row_num, karyawan_id in missing_rows:
            result.errors.append(
                KaryawanImportError(
                    row_num,
                    f'karyawan_id "{karyawan_id}" tidak ditemukan.',
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
