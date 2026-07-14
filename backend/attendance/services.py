"""Business logic for building RekapKehadiran rows from Jadwal/Absensi/Cuti/Liburan."""
from datetime import datetime, timedelta

from django.db import transaction

from cuti.models import Cuti, TipeCuti

from .models import (
    Absensi,
    Jadwal,
    Liburan,
    RekapKehadiran,
    StatusRekapKehadiran,
)

CUTI_TIPE_TO_STATUS = {
    TipeCuti.SAKIT: StatusRekapKehadiran.SAKIT,
    TipeCuti.IZIN_OFF: StatusRekapKehadiran.IZIN,
    TipeCuti.IZIN_TELAT: StatusRekapKehadiran.IZIN,
    TipeCuti.IZIN_PULANG_CEPAT: StatusRekapKehadiran.IZIN,
    TipeCuti.IZIN_LOKASI_BEDA: StatusRekapKehadiran.IZIN,
}


def _absensi_end_datetime(absensi: Absensi) -> datetime:
    return datetime.combine(absensi.tanggal, absensi.jam_masuk) + absensi.durasi


def _shift_end_datetime(tanggal, shift) -> datetime:
    end = datetime.combine(tanggal, shift.jam_keluar)
    if shift.jam_keluar <= shift.jam_masuk:
        end += timedelta(days=1)
    return end


def _resolve(jadwal, holiday_dates, cuti_map, absensi_map):
    """Return (status, absensi, cuti) for a single Jadwal entry."""
    tanggal = jadwal.tanggal

    if tanggal in holiday_dates:
        return StatusRekapKehadiran.LIBUR, None, None

    cuti = cuti_map.get((jadwal.karyawan_id, tanggal))
    if cuti is not None:
        status = CUTI_TIPE_TO_STATUS.get(cuti.tipe, StatusRekapKehadiran.CUTI)
        return status, None, cuti

    absensi = absensi_map.get((jadwal.karyawan_id, tanggal))
    if absensi is not None:
        if absensi.jam_masuk > jadwal.shift.jam_masuk:
            status = StatusRekapKehadiran.TERLAMBAT
        elif _absensi_end_datetime(absensi) < _shift_end_datetime(tanggal, jadwal.shift):
            status = StatusRekapKehadiran.PULANG_CEPAT
        else:
            status = StatusRekapKehadiran.HADIR
        return status, absensi, None

    return StatusRekapKehadiran.ALPA, None, None


@transaction.atomic
def process_rekap(tanggal_mulai, tanggal_selesai):
    """(Re)build RekapKehadiran rows for all Jadwal in the date range. Idempotent."""
    jadwal_qs = (
        Jadwal.objects.filter(tanggal__range=(tanggal_mulai, tanggal_selesai))
        .select_related('shift', 'karyawan')
    )

    holiday_dates = set(
        Liburan.objects.filter(
            tanggal__range=(tanggal_mulai, tanggal_selesai)
        ).values_list('tanggal', flat=True)
    )

    cuti_map = {
        (c.permohonan.karyawan_id, c.tanggal): c
        for c in Cuti.objects.filter(
            tanggal__range=(tanggal_mulai, tanggal_selesai)
        ).select_related('permohonan')
    }

    absensi_map = {
        (a.karyawan_id, a.tanggal): a
        for a in Absensi.objects.filter(
            tanggal__range=(tanggal_mulai, tanggal_selesai)
        )
    }

    RekapKehadiran.objects.filter(
        jadwal__tanggal__range=(tanggal_mulai, tanggal_selesai)
    ).delete()

    rekap_rows = []
    for jadwal in jadwal_qs:
        status, absensi, cuti = _resolve(jadwal, holiday_dates, cuti_map, absensi_map)
        rekap_rows.append(
            RekapKehadiran(jadwal=jadwal, absensi=absensi, cuti=cuti, status=status)
        )

    RekapKehadiran.objects.bulk_create(rekap_rows)
    return len(rekap_rows)
