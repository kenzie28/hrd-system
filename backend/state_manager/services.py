"""Export and restore the full HRD database state as a sectioned CSV."""

from __future__ import annotations

import csv
import io
import secrets
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.authtoken.models import Token

from absensi.models import Absensi
from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from gaji.models import GajiTemp
from karyawan.models import Karyawan
from karyawan.signals import ensure_portal_login
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from lokasi.models import Lokasi
from shift.models import HariKerja, Shift

from .constants import (
    STATE_FORMAT_MARKER,
    STATE_FORMAT_VERSION,
    STATE_MANAGER_PASSWORD,
    TABLE_ABSENSI,
    TABLE_AUTH_USER,
    TABLE_COLUMNS,
    TABLE_CUTI,
    TABLE_GAJI,
    TABLE_KARYAWAN,
    TABLE_LIBURAN,
    TABLE_LOKASI,
    TABLE_ORDER,
    TABLE_PERMOHONAN_CUTI,
    TABLE_PERMOHONAN_LEMBUR,
    TABLE_SHIFT,
)


@dataclass
class StateError:
    row: int
    message: str


@dataclass
class StateImportResult:
    errors: list[StateError] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def serialize_import_result(result: StateImportResult) -> dict:
    return {
        'ok': result.ok,
        'counts': result.counts,
        'errors': [{'row': e.row, 'message': e.message} for e in result.errors],
    }


def password_matches(provided: str | None) -> bool:
    candidate = (provided or '').encode('utf-8')
    expected = STATE_MANAGER_PASSWORD.encode('utf-8')
    if len(candidate) != len(expected):
        # compare_digest requires equal length; still do a dummy compare
        secrets.compare_digest(expected, expected)
        return False
    return secrets.compare_digest(candidate, expected)


def extract_password(request) -> str:
    header = request.META.get('HTTP_X_STATE_MANAGER_PASSWORD', '') or ''
    if header:
        return str(header)
    if request.method == 'GET':
        return str(request.query_params.get('password') or '')
    data = getattr(request, 'data', None)
    if data is not None:
        return str(data.get('password') or '')
    return ''


@contextmanager
def without_karyawan_login_signal():
    post_save.disconnect(ensure_portal_login, sender=Karyawan)
    try:
        yield
    finally:
        post_save.connect(ensure_portal_login, sender=Karyawan)


def _cell(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, timedelta):
        return _format_duration(value)
    if isinstance(value, datetime):
        dt = value
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, time):
        return value.strftime('%H:%M:%S')
    if isinstance(value, Decimal):
        return format(value, 'f')
    return str(value)


def _format_duration(td: timedelta) -> str:
    total = int(td.total_seconds())
    sign = '-' if total < 0 else ''
    total = abs(total)
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    return f'{sign}{hours:02d}:{minutes:02d}:{seconds:02d}'


def _write_table(writer: csv.writer, name: str, columns: tuple[str, ...], rows: list[list[str]]):
    writer.writerow(['__table__', name])
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)


def export_state_csv() -> str:
    """Serialize every HRD state table into a sectioned CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow([STATE_FORMAT_MARKER, STATE_FORMAT_VERSION])

    lokasi_rows = [
        [_cell(obj.id), _cell(obj.nama)]
        for obj in Lokasi.objects.order_by('id')
    ]
    _write_table(writer, TABLE_LOKASI, TABLE_COLUMNS[TABLE_LOKASI], lokasi_rows)

    user_ids = list(
        Karyawan.objects.exclude(user_id=None).values_list('user_id', flat=True)
    )
    user_rows = []
    for obj in User.objects.filter(pk__in=user_ids).order_by('id'):
        user_rows.append(
            [
                _cell(obj.id),
                _cell(obj.username),
                _cell(obj.password),
                _cell(obj.email),
                _cell(obj.is_active),
                _cell(obj.is_staff),
                _cell(obj.is_superuser),
                _cell(obj.date_joined),
                _cell(obj.last_login),
            ]
        )
    _write_table(writer, TABLE_AUTH_USER, TABLE_COLUMNS[TABLE_AUTH_USER], user_rows)

    karyawan_rows = []
    for obj in Karyawan.objects.order_by('karyawan_id'):
        karyawan_rows.append(
            [
                _cell(obj.karyawan_id),
                _cell(obj.nama),
                _cell(obj.lokasi_kerja_id),
                _cell(obj.jabatan),
                _cell(obj.wilayah),
                _cell(obj.level),
                _cell(obj.user_id),
                _cell(obj.must_change_password),
                _cell(obj.cuti_tahunan),
            ]
        )
    _write_table(writer, TABLE_KARYAWAN, TABLE_COLUMNS[TABLE_KARYAWAN], karyawan_rows)

    shift_rows = []
    for obj in Shift.objects.order_by('id'):
        shift_rows.append(
            [
                _cell(obj.id),
                _cell(obj.lokasi_kerja_id),
                _cell(obj.hari),
                _cell(obj.jam_masuk),
                _cell(obj.jam_keluar),
            ]
        )
    _write_table(writer, TABLE_SHIFT, TABLE_COLUMNS[TABLE_SHIFT], shift_rows)

    liburan_rows = [
        [_cell(obj.id), _cell(obj.nama), _cell(obj.tanggal)]
        for obj in Liburan.objects.order_by('id')
    ]
    _write_table(writer, TABLE_LIBURAN, TABLE_COLUMNS[TABLE_LIBURAN], liburan_rows)

    absensi_rows = []
    for obj in Absensi.objects.order_by('id'):
        absensi_rows.append(
            [
                _cell(obj.id),
                _cell(obj.karyawan_id),
                _cell(obj.lokasi_id),
                _cell(obj.tanggal),
                _cell(obj.jam_masuk),
                _cell(obj.durasi),
            ]
        )
    _write_table(writer, TABLE_ABSENSI, TABLE_COLUMNS[TABLE_ABSENSI], absensi_rows)

    permohonan_cuti_rows = []
    for obj in PermohonanCuti.objects.order_by('id'):
        permohonan_cuti_rows.append(
            [
                _cell(obj.id),
                _cell(obj.karyawan_id),
                _cell(obj.tipe),
                _cell(obj.alasan),
                _cell(obj.tanggal_mulai),
                _cell(obj.tanggal_selesai),
                _cell(obj.status),
                _cell(obj.supervisor_id),
                _cell(obj.hrd_approver_id),
            ]
        )
    _write_table(
        writer,
        TABLE_PERMOHONAN_CUTI,
        TABLE_COLUMNS[TABLE_PERMOHONAN_CUTI],
        permohonan_cuti_rows,
    )

    cuti_rows = [
        [_cell(obj.id), _cell(obj.permohonan_id), _cell(obj.tanggal)]
        for obj in Cuti.objects.order_by('id')
    ]
    _write_table(writer, TABLE_CUTI, TABLE_COLUMNS[TABLE_CUTI], cuti_rows)

    permohonan_lembur_rows = []
    for obj in PermohonanLembur.objects.order_by('id'):
        permohonan_lembur_rows.append(
            [
                _cell(obj.id),
                _cell(obj.karyawan_id),
                _cell(obj.alasan),
                _cell(obj.tanggal),
                _cell(obj.status),
                _cell(obj.supervisor_id),
                _cell(obj.hrd_approver_id),
            ]
        )
    _write_table(
        writer,
        TABLE_PERMOHONAN_LEMBUR,
        TABLE_COLUMNS[TABLE_PERMOHONAN_LEMBUR],
        permohonan_lembur_rows,
    )

    gaji_rows = []
    gaji_cols = TABLE_COLUMNS[TABLE_GAJI]
    for obj in GajiTemp.objects.order_by('id'):
        gaji_rows.append([_cell(getattr(obj, col)) for col in gaji_cols])
    _write_table(writer, TABLE_GAJI, gaji_cols, gaji_rows)

    return buf.getvalue()


def _blank_row(row: list[str]) -> bool:
    return all(not (cell or '').strip() for cell in row)


def parse_state_csv(text: str) -> tuple[dict[str, list[dict]], list[StateError]]:
    """Split a state CSV into table-name → row dicts (string values + _line)."""
    errors: list[StateError] = []
    tables: dict[str, list[dict]] = {}
    seen_headers: dict[str, list[str]] = {}

    reader = csv.reader(io.StringIO(text))
    seen_version = False
    current_table: str | None = None
    current_headers: list[str] | None = None
    expecting_headers = False

    for line_no, raw_row in enumerate(reader, start=1):
        if _blank_row(raw_row):
            continue
        row = [(cell or '').strip() for cell in raw_row]

        if not seen_version:
            marker = row[0] if row else ''
            version = row[1] if len(row) > 1 else ''
            if marker != STATE_FORMAT_MARKER or version != STATE_FORMAT_VERSION:
                errors.append(
                    StateError(
                        line_no,
                        'File bukan snapshot hrd-system-state v1.',
                    )
                )
                return tables, errors
            seen_version = True
            continue

        if row and row[0] == '__table__':
            if expecting_headers:
                errors.append(
                    StateError(
                        line_no,
                        f'Tabel "{current_table}" tidak memiliki baris header.',
                    )
                )
            name = row[1] if len(row) > 1 else ''
            if not name:
                errors.append(StateError(line_no, 'Nama tabel kosong pada penanda __table__.'))
                current_table = None
                current_headers = None
                expecting_headers = False
                continue
            if name not in TABLE_COLUMNS:
                errors.append(StateError(line_no, f'Tabel tidak dikenal: "{name}".'))
                current_table = None
                current_headers = None
                expecting_headers = False
                continue
            if name in tables:
                errors.append(StateError(line_no, f'Tabel "{name}" muncul lebih dari sekali.'))
                current_table = None
                current_headers = None
                expecting_headers = False
                continue
            tables[name] = []
            current_table = name
            current_headers = None
            expecting_headers = True
            continue

        if expecting_headers:
            expected = TABLE_COLUMNS[current_table]
            received = tuple(row)
            seen_headers[current_table] = list(received)
            missing = [c for c in expected if c not in received]
            extra = [c for c in received if c not in expected]
            if missing or extra:
                parts = []
                if missing:
                    parts.append('kolom wajib hilang: ' + ', '.join(missing))
                if extra:
                    parts.append('kolom tidak dikenal: ' + ', '.join(extra))
                errors.append(
                    StateError(
                        line_no,
                        f'Tabel "{current_table}": {"; ".join(parts)}.',
                    )
                )
            current_headers = list(received)
            expecting_headers = False
            continue

        if current_table is None or current_headers is None:
            errors.append(StateError(line_no, 'Baris data muncul sebelum penanda __table__.'))
            continue

        padded = row + [''] * (len(current_headers) - len(row))
        record = {
            header: padded[i] if i < len(padded) else ''
            for i, header in enumerate(current_headers)
        }
        record['_line'] = str(line_no)
        tables[current_table].append(record)

    if not seen_version:
        errors.append(StateError(0, 'File bukan snapshot hrd-system-state v1.'))

    if expecting_headers:
        errors.append(
            StateError(0, f'Tabel "{current_table}" tidak memiliki baris header.')
        )

    for name in TABLE_ORDER:
        if name not in tables:
            errors.append(StateError(0, f'Tabel "{name}" tidak ada di file.'))

    return tables, errors


def _line_of(row: dict) -> int:
    try:
        return int(row.get('_line') or 0)
    except (TypeError, ValueError):
        return 0


def _req(row: dict, field: str, errors: list[StateError], table: str) -> str | None:
    value = (row.get(field) or '').strip()
    if not value:
        errors.append(
            StateError(_line_of(row), f'{table}.{field} wajib diisi.')
        )
        return None
    return value


def _opt(row: dict, field: str) -> str:
    return (row.get(field) or '').strip()


def _parse_bool(raw: str, line: int, field: str, errors: list[StateError]) -> bool | None:
    value = raw.strip().lower()
    if value in ('true', '1', 'yes'):
        return True
    if value in ('false', '0', 'no'):
        return False
    errors.append(StateError(line, f'{field} harus true atau false.'))
    return None


def _parse_int(raw: str, line: int, field: str, errors: list[StateError]) -> int | None:
    value = raw.strip()
    if not value:
        errors.append(StateError(line, f'{field} wajib diisi.'))
        return None
    try:
        return int(value)
    except ValueError:
        errors.append(StateError(line, f'{field} harus berupa bilangan bulat.'))
        return None


def _parse_opt_int(raw: str, line: int, field: str, errors: list[StateError]) -> int | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        errors.append(StateError(line, f'{field} harus berupa bilangan bulat.'))
        return None


def _parse_date(raw: str, line: int, field: str, errors: list[StateError]) -> date | None:
    value = raw.strip()
    if not value:
        errors.append(StateError(line, f'{field} wajib diisi.'))
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        errors.append(StateError(line, f'{field} harus berformat YYYY-MM-DD.'))
        return None


def _parse_time(raw: str, line: int, field: str, errors: list[StateError]) -> time | None:
    value = raw.strip()
    if not value:
        errors.append(StateError(line, f'{field} wajib diisi.'))
        return None
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    errors.append(StateError(line, f'{field} harus berformat HH:MM atau HH:MM:SS.'))
    return None


def _parse_duration(raw: str, line: int, field: str, errors: list[StateError]) -> timedelta | None:
    value = raw.strip()
    if not value:
        errors.append(StateError(line, f'{field} wajib diisi.'))
        return None
    sign = 1
    if value.startswith('-'):
        sign = -1
        value = value[1:]
    parts = value.split(':')
    if len(parts) != 3:
        errors.append(StateError(line, f'{field} harus berformat HH:MM:SS.'))
        return None
    try:
        hours, minutes, seconds = (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        errors.append(StateError(line, f'{field} harus berformat HH:MM:SS.'))
        return None
    if minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59:
        errors.append(StateError(line, f'{field} menit/detik tidak valid.'))
        return None
    return sign * timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _parse_datetime(raw: str, line: int, field: str, errors: list[StateError], *, required: bool):
    value = raw.strip()
    if not value:
        if required:
            errors.append(StateError(line, f'{field} wajib diisi.'))
        return None
    dt = parse_datetime(value.replace(' ', 'T', 1))
    if dt is None:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                dt = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        errors.append(
            StateError(line, f'{field} harus berformat YYYY-MM-DD HH:MM:SS.')
        )
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt


def _parse_decimal(raw: str, line: int, field: str, errors: list[StateError]) -> Decimal | None:
    value = raw.strip()
    if not value:
        errors.append(StateError(line, f'{field} wajib diisi.'))
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        errors.append(StateError(line, f'{field} harus berupa angka.'))
        return None


def _choice(raw: str, allowed: set[str], line: int, field: str, errors: list[StateError]) -> str | None:
    value = raw.strip()
    if value not in allowed:
        errors.append(
            StateError(line, f'{field} tidak valid: "{value}".')
        )
        return None
    return value


def _normalize_and_validate(tables: dict[str, list[dict]]) -> tuple[dict, list[StateError]]:
    errors: list[StateError] = []
    typed: dict[str, list[dict]] = {name: [] for name in TABLE_ORDER}

    lokasi_ids: set[str] = set()
    for row in tables.get(TABLE_LOKASI, []):
        line = _line_of(row)
        pk = _req(row, 'id', errors, TABLE_LOKASI)
        nama = _req(row, 'nama', errors, TABLE_LOKASI)
        if pk is None or nama is None:
            continue
        if len(pk) > 2:
            errors.append(StateError(line, 'lokasi.id maksimal 2 karakter.'))
            continue
        if pk in lokasi_ids:
            errors.append(StateError(line, f'lokasi.id duplikat: {pk}.'))
            continue
        lokasi_ids.add(pk)
        typed[TABLE_LOKASI].append({'id': pk, 'nama': nama, '_line': line})

    user_ids: set[int] = set()
    usernames: set[str] = set()
    for row in tables.get(TABLE_AUTH_USER, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'auth_user.id', errors)
        username = _req(row, 'username', errors, TABLE_AUTH_USER)
        password = _req(row, 'password', errors, TABLE_AUTH_USER)
        is_active = _parse_bool(_opt(row, 'is_active') or 'true', line, 'is_active', errors)
        is_staff = _parse_bool(_opt(row, 'is_staff') or 'false', line, 'is_staff', errors)
        is_superuser = _parse_bool(
            _opt(row, 'is_superuser') or 'false', line, 'is_superuser', errors
        )
        date_joined = _parse_datetime(
            _opt(row, 'date_joined'), line, 'date_joined', errors, required=True
        )
        last_login = _parse_datetime(
            _opt(row, 'last_login'), line, 'last_login', errors, required=False
        )
        if None in (pk, username, password, is_active, is_staff, is_superuser, date_joined):
            continue
        if pk in user_ids:
            errors.append(StateError(line, f'auth_user.id duplikat: {pk}.'))
            continue
        if username in usernames:
            errors.append(StateError(line, f'auth_user.username duplikat: {username}.'))
            continue
        user_ids.add(pk)
        usernames.add(username)
        typed[TABLE_AUTH_USER].append(
            {
                'id': pk,
                'username': username,
                'password': password,
                'email': _opt(row, 'email'),
                'is_active': is_active,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
                'date_joined': date_joined,
                'last_login': last_login,
                '_line': line,
            }
        )

    karyawan_ids: set[str] = set()
    for row in tables.get(TABLE_KARYAWAN, []):
        line = _line_of(row)
        kid = _req(row, 'karyawan_id', errors, TABLE_KARYAWAN)
        nama = _req(row, 'nama', errors, TABLE_KARYAWAN)
        level = _parse_int(_opt(row, 'level'), line, 'level', errors)
        must_change = _parse_bool(
            _opt(row, 'must_change_password') or 'true',
            line,
            'must_change_password',
            errors,
        )
        cuti_tahunan = _parse_int(
            _opt(row, 'cuti_tahunan') or '12', line, 'cuti_tahunan', errors
        )
        lokasi_kerja_id = _opt(row, 'lokasi_kerja_id') or None
        user_id = _parse_opt_int(_opt(row, 'user_id'), line, 'user_id', errors)
        if None in (kid, nama, level, must_change, cuti_tahunan):
            continue
        if kid in karyawan_ids:
            errors.append(StateError(line, f'karyawan_id duplikat: {kid}.'))
            continue
        if lokasi_kerja_id and lokasi_kerja_id not in lokasi_ids:
            errors.append(
                StateError(line, f'lokasi_kerja_id tidak ada di tabel lokasi: {lokasi_kerja_id}.')
            )
            continue
        if user_id is not None and user_id not in user_ids:
            errors.append(
                StateError(line, f'user_id tidak ada di tabel auth_user: {user_id}.')
            )
            continue
        if not 1 <= level <= 8:
            errors.append(StateError(line, 'level harus 1–8.'))
            continue
        karyawan_ids.add(kid)
        typed[TABLE_KARYAWAN].append(
            {
                'karyawan_id': kid,
                'nama': nama,
                'lokasi_kerja_id': lokasi_kerja_id,
                'jabatan': _opt(row, 'jabatan'),
                'wilayah': _opt(row, 'wilayah'),
                'level': level,
                'user_id': user_id,
                'must_change_password': must_change,
                'cuti_tahunan': cuti_tahunan,
                '_line': line,
            }
        )

    hari_values = {choice.value for choice in HariKerja}
    shift_ids: set[int] = set()
    for row in tables.get(TABLE_SHIFT, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'shift.id', errors)
        lokasi_kerja_id = _req(row, 'lokasi_kerja_id', errors, TABLE_SHIFT)
        hari = _choice(_opt(row, 'hari'), hari_values, line, 'hari', errors)
        jam_masuk = _parse_time(_opt(row, 'jam_masuk'), line, 'jam_masuk', errors)
        jam_keluar = _parse_time(_opt(row, 'jam_keluar'), line, 'jam_keluar', errors)
        if None in (pk, lokasi_kerja_id, hari, jam_masuk, jam_keluar):
            continue
        if pk in shift_ids:
            errors.append(StateError(line, f'shift.id duplikat: {pk}.'))
            continue
        if lokasi_kerja_id not in lokasi_ids:
            errors.append(
                StateError(line, f'lokasi_kerja_id tidak ada di tabel lokasi: {lokasi_kerja_id}.')
            )
            continue
        shift_ids.add(pk)
        typed[TABLE_SHIFT].append(
            {
                'id': pk,
                'lokasi_kerja_id': lokasi_kerja_id,
                'hari': hari,
                'jam_masuk': jam_masuk,
                'jam_keluar': jam_keluar,
                '_line': line,
            }
        )

    liburan_ids: set[int] = set()
    for row in tables.get(TABLE_LIBURAN, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'liburan.id', errors)
        nama = _req(row, 'nama', errors, TABLE_LIBURAN)
        tanggal = _parse_date(_opt(row, 'tanggal'), line, 'tanggal', errors)
        if None in (pk, nama, tanggal):
            continue
        if pk in liburan_ids:
            errors.append(StateError(line, f'liburan.id duplikat: {pk}.'))
            continue
        liburan_ids.add(pk)
        typed[TABLE_LIBURAN].append(
            {'id': pk, 'nama': nama, 'tanggal': tanggal, '_line': line}
        )

    absensi_ids: set[int] = set()
    absensi_keys: set[tuple] = set()
    for row in tables.get(TABLE_ABSENSI, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'absensi.id', errors)
        karyawan_id = _req(row, 'karyawan_id', errors, TABLE_ABSENSI)
        lokasi_id = _req(row, 'lokasi_id', errors, TABLE_ABSENSI)
        tanggal = _parse_date(_opt(row, 'tanggal'), line, 'tanggal', errors)
        jam_masuk = _parse_time(_opt(row, 'jam_masuk'), line, 'jam_masuk', errors)
        durasi = _parse_duration(_opt(row, 'durasi'), line, 'durasi', errors)
        if None in (pk, karyawan_id, lokasi_id, tanggal, jam_masuk, durasi):
            continue
        if pk in absensi_ids:
            errors.append(StateError(line, f'absensi.id duplikat: {pk}.'))
            continue
        if karyawan_id not in karyawan_ids:
            errors.append(StateError(line, f'karyawan_id tidak ada: {karyawan_id}.'))
            continue
        if lokasi_id not in lokasi_ids:
            errors.append(StateError(line, f'lokasi_id tidak ada: {lokasi_id}.'))
            continue
        key = (karyawan_id, lokasi_id, tanggal, jam_masuk, durasi)
        if key in absensi_keys:
            errors.append(StateError(line, 'Baris absensi duplikat (karyawan/lokasi/tanggal/jam/durasi).'))
            continue
        absensi_ids.add(pk)
        absensi_keys.add(key)
        typed[TABLE_ABSENSI].append(
            {
                'id': pk,
                'karyawan_id': karyawan_id,
                'lokasi_id': lokasi_id,
                'tanggal': tanggal,
                'jam_masuk': jam_masuk,
                'durasi': durasi,
                '_line': line,
            }
        )

    tipe_cuti = {choice.value for choice in TipeCuti}
    status_cuti = {choice.value for choice in StatusPermohonanCuti}
    permohonan_cuti_ids: set[int] = set()
    for row in tables.get(TABLE_PERMOHONAN_CUTI, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'permohonan_cuti.id', errors)
        karyawan_id = _req(row, 'karyawan_id', errors, TABLE_PERMOHONAN_CUTI)
        tipe = _choice(_opt(row, 'tipe'), tipe_cuti, line, 'tipe', errors)
        tanggal_mulai = _parse_date(_opt(row, 'tanggal_mulai'), line, 'tanggal_mulai', errors)
        tanggal_selesai = _parse_date(
            _opt(row, 'tanggal_selesai'), line, 'tanggal_selesai', errors
        )
        status = _choice(_opt(row, 'status'), status_cuti, line, 'status', errors)
        supervisor_id = _opt(row, 'supervisor_id') or None
        hrd_approver_id = _opt(row, 'hrd_approver_id') or None
        if None in (pk, karyawan_id, tipe, tanggal_mulai, tanggal_selesai, status):
            continue
        if pk in permohonan_cuti_ids:
            errors.append(StateError(line, f'permohonan_cuti.id duplikat: {pk}.'))
            continue
        if karyawan_id not in karyawan_ids:
            errors.append(StateError(line, f'karyawan_id tidak ada: {karyawan_id}.'))
            continue
        if supervisor_id and supervisor_id not in karyawan_ids:
            errors.append(StateError(line, f'supervisor_id tidak ada: {supervisor_id}.'))
            continue
        if hrd_approver_id and hrd_approver_id not in karyawan_ids:
            errors.append(StateError(line, f'hrd_approver_id tidak ada: {hrd_approver_id}.'))
            continue
        permohonan_cuti_ids.add(pk)
        typed[TABLE_PERMOHONAN_CUTI].append(
            {
                'id': pk,
                'karyawan_id': karyawan_id,
                'tipe': tipe,
                'alasan': row.get('alasan') or '',
                'tanggal_mulai': tanggal_mulai,
                'tanggal_selesai': tanggal_selesai,
                'status': status,
                'supervisor_id': supervisor_id,
                'hrd_approver_id': hrd_approver_id,
                '_line': line,
            }
        )

    cuti_ids: set[int] = set()
    for row in tables.get(TABLE_CUTI, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'cuti.id', errors)
        permohonan_id = _parse_int(_opt(row, 'permohonan_id'), line, 'permohonan_id', errors)
        tanggal = _parse_date(_opt(row, 'tanggal'), line, 'tanggal', errors)
        if None in (pk, permohonan_id, tanggal):
            continue
        if pk in cuti_ids:
            errors.append(StateError(line, f'cuti.id duplikat: {pk}.'))
            continue
        if permohonan_id not in permohonan_cuti_ids:
            errors.append(
                StateError(line, f'permohonan_id tidak ada di permohonan_cuti: {permohonan_id}.')
            )
            continue
        cuti_ids.add(pk)
        typed[TABLE_CUTI].append(
            {
                'id': pk,
                'permohonan_id': permohonan_id,
                'tanggal': tanggal,
                '_line': line,
            }
        )

    status_lembur = {choice.value for choice in StatusPermohonanLembur}
    lembur_ids: set[int] = set()
    for row in tables.get(TABLE_PERMOHONAN_LEMBUR, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'permohonan_lembur.id', errors)
        karyawan_id = _req(row, 'karyawan_id', errors, TABLE_PERMOHONAN_LEMBUR)
        tanggal = _parse_date(_opt(row, 'tanggal'), line, 'tanggal', errors)
        status = _choice(_opt(row, 'status'), status_lembur, line, 'status', errors)
        supervisor_id = _opt(row, 'supervisor_id') or None
        hrd_approver_id = _opt(row, 'hrd_approver_id') or None
        if None in (pk, karyawan_id, tanggal, status):
            continue
        if pk in lembur_ids:
            errors.append(StateError(line, f'permohonan_lembur.id duplikat: {pk}.'))
            continue
        if karyawan_id not in karyawan_ids:
            errors.append(StateError(line, f'karyawan_id tidak ada: {karyawan_id}.'))
            continue
        if supervisor_id and supervisor_id not in karyawan_ids:
            errors.append(StateError(line, f'supervisor_id tidak ada: {supervisor_id}.'))
            continue
        if hrd_approver_id and hrd_approver_id not in karyawan_ids:
            errors.append(StateError(line, f'hrd_approver_id tidak ada: {hrd_approver_id}.'))
            continue
        lembur_ids.add(pk)
        typed[TABLE_PERMOHONAN_LEMBUR].append(
            {
                'id': pk,
                'karyawan_id': karyawan_id,
                'alasan': row.get('alasan') or '',
                'tanggal': tanggal,
                'status': status,
                'supervisor_id': supervisor_id,
                'hrd_approver_id': hrd_approver_id,
                '_line': line,
            }
        )

    gaji_ids: set[int] = set()
    gaji_keys: set[tuple] = set()
    int_gaji_fields = (
        'total_hadir',
        'hari_sakit',
        'hari_cuti',
        'hari_cuti_tambahan',
        'freq_pencapaian_target',
        'rate_target',
        'rate_non_target',
        'gaji_pokok',
        'rate_uang_makan',
        'rate_lembur_6_jam',
        'freq_hari_raya',
        'tunjangan_lama_kerja',
        'tunjangan_obat',
        'freq_alpa',
        'pot_bpjs_jht',
        'pot_bpjs_jp',
        'pot_bpjs_kesehatan',
        'pot_pph21',
        'pot_kehilangan',
        'koreksi_absensi',
        'total_gaji',
    )
    for row in tables.get(TABLE_GAJI, []):
        line = _line_of(row)
        pk = _parse_int(_opt(row, 'id'), line, 'gaji.id', errors)
        karyawan_id = _req(row, 'karyawan_id', errors, TABLE_GAJI)
        periode = _parse_date(_opt(row, 'periode'), line, 'periode', errors)
        freq_lembur = _parse_decimal(
            _opt(row, 'freq_lembur_6_jam') or '0', line, 'freq_lembur_6_jam', errors
        )
        created_at = _parse_datetime(
            _opt(row, 'created_at'), line, 'created_at', errors, required=False
        )
        updated_at = _parse_datetime(
            _opt(row, 'updated_at'), line, 'updated_at', errors, required=False
        )
        ints: dict[str, int | None] = {}
        for fname in int_gaji_fields:
            ints[fname] = _parse_int(_opt(row, fname) or '0', line, fname, errors)
        if None in (pk, karyawan_id, periode, freq_lembur) or any(v is None for v in ints.values()):
            continue
        if pk in gaji_ids:
            errors.append(StateError(line, f'gaji.id duplikat: {pk}.'))
            continue
        if karyawan_id not in karyawan_ids:
            errors.append(StateError(line, f'karyawan_id tidak ada: {karyawan_id}.'))
            continue
        key = (karyawan_id, periode)
        if key in gaji_keys:
            errors.append(StateError(line, f'gaji duplikat untuk {karyawan_id} periode {periode}.'))
            continue
        gaji_ids.add(pk)
        gaji_keys.add(key)
        record = {
            'id': pk,
            'karyawan_id': karyawan_id,
            'periode': periode,
            'hadir': _opt(row, 'hadir'),
            'freq_lembur_6_jam': freq_lembur,
            'created_at': created_at,
            'updated_at': updated_at,
            '_line': line,
        }
        record.update(ints)
        typed[TABLE_GAJI].append(record)

    karyawan_user_ids = set(
        Karyawan.objects.exclude(user_id=None).values_list('user_id', flat=True)
    )
    unlinked_users = User.objects.exclude(pk__in=karyawan_user_ids)
    csv_user_ids = {row['id'] for row in typed[TABLE_AUTH_USER]}
    csv_usernames = {row['username'] for row in typed[TABLE_AUTH_USER]}
    for user in unlinked_users:
        if user.id in csv_user_ids:
            errors.append(
                StateError(
                    0,
                    f'auth_user.id {user.id} bentrok dengan akun Django yang dipertahankan ({user.username}).',
                )
            )
        elif user.username in csv_usernames:
            errors.append(
                StateError(
                    0,
                    f'auth_user.username "{user.username}" bentrok dengan akun Django yang dipertahankan.',
                )
            )

    return typed, errors


def _wipe_hrd_state() -> list[int]:
    """Delete HRD rows. Returns karyawan-linked user ids that should be removed."""
    linked_user_ids = list(
        Karyawan.objects.exclude(user_id=None).values_list('user_id', flat=True)
    )
    GajiTemp.objects.all().delete()
    PermohonanLembur.objects.all().delete()
    Cuti.objects.all().delete()
    PermohonanCuti.objects.all().delete()
    Absensi.objects.all().delete()
    Shift.objects.all().delete()
    Liburan.objects.all().delete()
    Token.objects.filter(user_id__in=linked_user_ids).delete()
    Karyawan.objects.all().delete()
    if linked_user_ids:
        User.objects.filter(pk__in=linked_user_ids).delete()
    Lokasi.objects.all().delete()
    return linked_user_ids


def _insert_state(typed: dict[str, list[dict]]) -> None:
    for row in typed[TABLE_LOKASI]:
        Lokasi.objects.create(id=row['id'], nama=row['nama'])

    for row in typed[TABLE_AUTH_USER]:
        User.objects.create(
            id=row['id'],
            username=row['username'],
            password=row['password'],
            email=row['email'],
            is_active=row['is_active'],
            is_staff=row['is_staff'],
            is_superuser=row['is_superuser'],
            date_joined=row['date_joined'],
            last_login=row['last_login'],
        )

    for row in typed[TABLE_KARYAWAN]:
        Karyawan.objects.create(
            karyawan_id=row['karyawan_id'],
            nama=row['nama'],
            lokasi_kerja_id=row['lokasi_kerja_id'],
            jabatan=row['jabatan'],
            wilayah=row['wilayah'],
            level=row['level'],
            user_id=row['user_id'],
            must_change_password=row['must_change_password'],
            cuti_tahunan=row['cuti_tahunan'],
        )

    for row in typed[TABLE_SHIFT]:
        Shift.objects.create(
            id=row['id'],
            lokasi_kerja_id=row['lokasi_kerja_id'],
            hari=row['hari'],
            jam_masuk=row['jam_masuk'],
            jam_keluar=row['jam_keluar'],
        )

    for row in typed[TABLE_LIBURAN]:
        Liburan.objects.create(id=row['id'], nama=row['nama'], tanggal=row['tanggal'])

    for row in typed[TABLE_ABSENSI]:
        Absensi.objects.create(
            id=row['id'],
            karyawan_id=row['karyawan_id'],
            lokasi_id=row['lokasi_id'],
            tanggal=row['tanggal'],
            jam_masuk=row['jam_masuk'],
            durasi=row['durasi'],
        )

    for row in typed[TABLE_PERMOHONAN_CUTI]:
        PermohonanCuti.objects.create(
            id=row['id'],
            karyawan_id=row['karyawan_id'],
            tipe=row['tipe'],
            alasan=row['alasan'],
            tanggal_mulai=row['tanggal_mulai'],
            tanggal_selesai=row['tanggal_selesai'],
            status=row['status'],
            supervisor_id=row['supervisor_id'],
            hrd_approver_id=row['hrd_approver_id'],
        )

    for row in typed[TABLE_CUTI]:
        Cuti.objects.create(
            id=row['id'],
            permohonan_id=row['permohonan_id'],
            tanggal=row['tanggal'],
        )

    for row in typed[TABLE_PERMOHONAN_LEMBUR]:
        PermohonanLembur.objects.create(
            id=row['id'],
            karyawan_id=row['karyawan_id'],
            alasan=row['alasan'],
            tanggal=row['tanggal'],
            status=row['status'],
            supervisor_id=row['supervisor_id'],
            hrd_approver_id=row['hrd_approver_id'],
        )

    for row in typed[TABLE_GAJI]:
        obj = GajiTemp(
            id=row['id'],
            karyawan_id=row['karyawan_id'],
            periode=row['periode'],
            hadir=row['hadir'],
            total_hadir=row['total_hadir'],
            hari_sakit=row['hari_sakit'],
            hari_cuti=row['hari_cuti'],
            hari_cuti_tambahan=row['hari_cuti_tambahan'],
            freq_pencapaian_target=row['freq_pencapaian_target'],
            rate_target=row['rate_target'],
            rate_non_target=row['rate_non_target'],
            gaji_pokok=row['gaji_pokok'],
            rate_uang_makan=row['rate_uang_makan'],
            freq_lembur_6_jam=row['freq_lembur_6_jam'],
            rate_lembur_6_jam=row['rate_lembur_6_jam'],
            freq_hari_raya=row['freq_hari_raya'],
            tunjangan_lama_kerja=row['tunjangan_lama_kerja'],
            tunjangan_obat=row['tunjangan_obat'],
            freq_alpa=row['freq_alpa'],
            pot_bpjs_jht=row['pot_bpjs_jht'],
            pot_bpjs_jp=row['pot_bpjs_jp'],
            pot_bpjs_kesehatan=row['pot_bpjs_kesehatan'],
            pot_pph21=row['pot_pph21'],
            pot_kehilangan=row['pot_kehilangan'],
            koreksi_absensi=row['koreksi_absensi'],
            total_gaji=row['total_gaji'],
        )
        obj.save()
        update_fields = []
        if row.get('created_at') is not None:
            obj.created_at = row['created_at']
            update_fields.append('created_at')
        if row.get('updated_at') is not None:
            obj.updated_at = row['updated_at']
            update_fields.append('updated_at')
        if update_fields:
            obj.save(update_fields=update_fields)


def import_state_csv(text: str) -> StateImportResult:
    """Validate the snapshot, then atomically replace live HRD data with it."""
    result = StateImportResult()
    tables, parse_errors = parse_state_csv(text)
    if parse_errors:
        result.errors = parse_errors
        return result

    typed, validate_errors = _normalize_and_validate(tables)
    if validate_errors:
        result.errors = validate_errors
        return result

    try:
        with without_karyawan_login_signal():
            with transaction.atomic():
                _wipe_hrd_state()
                _insert_state(typed)
    except Exception as exc:  # noqa: BLE001 — surface any DB failure as import error
        result.errors.append(
            StateError(0, f'Gagal menyimpan state: {exc}')
        )
        return result

    result.counts = {name: len(typed.get(name, [])) for name in TABLE_ORDER}
    return result
