"""
Self-contained payroll database import for Karyawan, Lokasi, and Absensi.

Reads from the ERP MySQL server at 192.168.0.224 (payroll data in database `payroll`) and writes
into the HRD default DB. Remove this module and `import_payroll_absensi` management
command when no longer needed.

Environment variables (all optional):
  PAYROLL_DB_HOST     default: 192.168.0.224
  PAYROLL_DB_PORT     default: 3306
  PAYROLL_DB_USER     default: admin
  PAYROLL_DB_PASSWORD default: allow
  PAYROLL_DB_NAME     default: payroll

Usage:
  python manage.py import_payroll_absensi
  python manage.py import_payroll_absensi --dry-run
  python manage.py import_payroll_absensi --id-counter 99
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

import pymysql
from django.db import transaction

from attendance.models import Absensi
from core.models import Karyawan, Lokasi

DEFAULT_ID_COUNTER = '99'
DEFAULT_LOKASI_NAMA = 'HO'


@dataclass
class ImportResult:
    karyawan_created: int = 0
    karyawan_existing: int = 0
    lokasi_created: bool = False
    absensi_created: int = 0
    absensi_updated: int = 0
    absensi_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _payroll_connection_kwargs() -> dict[str, Any]:
    return {
        'host': os.environ.get('PAYROLL_DB_HOST', '192.168.0.224'),
        'port': int(os.environ.get('PAYROLL_DB_PORT', '3306')),
        'user': os.environ.get('PAYROLL_DB_USER', 'admin'),
        'password': os.environ.get('PAYROLL_DB_PASSWORD', 'allow'),
        'database': os.environ.get('PAYROLL_DB_NAME', 'payroll'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
    }


def _normalize_counter_id(id_counter: str) -> str:
    return str(id_counter).strip().zfill(2)[-2:]


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text or text.startswith('0000'):
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: Any) -> time | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return time(total // 3600 % 24, total % 3600 // 60, total % 60)
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _compute_durasi(
    tgl_masuk: date,
    jam_masuk: time,
    tgl_keluar: date,
    jam_keluar: time,
) -> timedelta:
    start = datetime.combine(tgl_masuk, jam_masuk)
    end = datetime.combine(tgl_keluar, jam_keluar)
    if end < start:
        end += timedelta(days=1)
    return end - start


def _fetch_karyawan_rows(cursor) -> list[dict[str, Any]]:
    cursor.execute('SELECT id_karyawan, nama_karyawan FROM sr_empl')
    return list(cursor.fetchall())


def _fetch_absensi_rows(cursor, id_counter: str) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT tgl_absen, tgl_absen_keluar, id_karyawan, masuk, keluar
        FROM sr_absensi
        WHERE id_counter = %s
        """,
        (id_counter,),
    )
    return list(cursor.fetchall())


def _build_nama_lookup(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Map payroll id_karyawan -> nama_karyawan from sr_empl (no DB writes)."""
    lookup: dict[str, str] = {}
    for row in rows:
        payroll_id = str(row['id_karyawan']).strip()
        nama = str(row.get('nama_karyawan') or '').strip()
        if payroll_id and nama:
            lookup[payroll_id] = nama
    return lookup


def _get_or_create_karyawan(
    payroll_id: str,
    nama_lookup: dict[str, str],
    karyawan_map: dict[str, Karyawan],
    result: ImportResult,
    *,
    dry_run: bool = False,
) -> Karyawan | None:
    if payroll_id in karyawan_map:
        return karyawan_map[payroll_id]

    nama = nama_lookup.get(payroll_id)
    if not nama:
        return None

    if dry_run:
        karyawan = Karyawan.objects.filter(nama=nama).first()
        if karyawan is None:
            result.karyawan_created += 1
            karyawan_map[payroll_id] = Karyawan(nama=nama)
        else:
            result.karyawan_existing += 1
            karyawan_map[payroll_id] = karyawan
        return karyawan_map[payroll_id]

    karyawan, created = Karyawan.objects.get_or_create(nama=nama)
    karyawan_map[payroll_id] = karyawan
    if created:
        result.karyawan_created += 1
    else:
        result.karyawan_existing += 1
    return karyawan


def _ensure_lokasi(lokasi_id: str, nama: str, result: ImportResult) -> Lokasi:
    lokasi, created = Lokasi.objects.get_or_create(
        id=lokasi_id,
        defaults={'nama': nama},
    )
    result.lokasi_created = created
    return lokasi


def _import_absensi_rows(
    rows: list[dict[str, Any]],
    nama_lookup: dict[str, str],
    karyawan_map: dict[str, Karyawan],
    lokasi: Lokasi,
    result: ImportResult,
    *,
    dry_run: bool,
) -> None:
    for row in rows:
        payroll_id = str(row['id_karyawan']).strip()
        karyawan = _get_or_create_karyawan(
            payroll_id, nama_lookup, karyawan_map, result, dry_run=dry_run
        )
        if karyawan is None:
            result.absensi_skipped += 1
            result.errors.append(
                f'No sr_empl match for payroll id_karyawan={payroll_id!r}'
            )
            continue

        tanggal = _parse_date(row.get('tgl_absen'))
        tgl_keluar = _parse_date(row.get('tgl_absen_keluar')) or tanggal
        jam_masuk = _parse_time(row.get('masuk'))
        jam_keluar = _parse_time(row.get('keluar'))

        if tanggal is None or jam_masuk is None or jam_keluar is None:
            result.absensi_skipped += 1
            result.errors.append(
                f'Skipped absensi for payroll id_karyawan={payroll_id!r}: invalid date/time'
            )
            continue

        durasi = _compute_durasi(tanggal, jam_masuk, tgl_keluar, jam_keluar)

        if dry_run:
            if karyawan.pk:
                existing = Absensi.objects.filter(
                    karyawan=karyawan, tanggal=tanggal
                ).exists()
            else:
                existing = False
            if existing:
                result.absensi_updated += 1
            else:
                result.absensi_created += 1
            continue

        absensi, created = Absensi.objects.update_or_create(
            karyawan=karyawan,
            tanggal=tanggal,
            defaults={
                'lokasi': lokasi,
                'jam_masuk': jam_masuk,
                'durasi': durasi,
            },
        )
        if created:
            result.absensi_created += 1
        else:
            result.absensi_updated += 1


@transaction.atomic
def import_payroll_absensi(
    *,
    id_counter: str = DEFAULT_ID_COUNTER,
    lokasi_nama: str = DEFAULT_LOKASI_NAMA,
    dry_run: bool = False,
) -> ImportResult:
    lokasi_id = _normalize_counter_id(id_counter)
    result = ImportResult()

    connection = pymysql.connect(**_payroll_connection_kwargs())
    try:
        with connection.cursor() as cursor:
            karyawan_rows = _fetch_karyawan_rows(cursor)
            absensi_rows = _fetch_absensi_rows(cursor, id_counter)

        nama_lookup = _build_nama_lookup(karyawan_rows)
        karyawan_map: dict[str, Karyawan] = {}
        lokasi = _ensure_lokasi(lokasi_id, lokasi_nama, result)
        _import_absensi_rows(
            absensi_rows,
            nama_lookup,
            karyawan_map,
            lokasi,
            result,
            dry_run=dry_run,
        )

        if dry_run:
            transaction.set_rollback(True)
    finally:
        connection.close()

    return result
