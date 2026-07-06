from datetime import date, time, timedelta

from django.test import TestCase

from attendance.models import Absensi
from attendance.services import _absensi_end_datetime, _shift_end_datetime
from core.models import Karyawan, Lokasi


class AbsensiKeluarHariOffsetTests(TestCase):
    def setUp(self):
        self.karyawan = Karyawan.objects.create(nama='Test')
        self.lokasi = Lokasi.objects.create(id='HQ', nama='HQ')

    def _make_absensi(self, tanggal, jam_masuk, durasi):
        return Absensi.objects.create(
            karyawan=self.karyawan,
            lokasi=self.lokasi,
            tanggal=tanggal,
            jam_masuk=jam_masuk,
            durasi=durasi,
        )

    def test_same_day_keluar_has_zero_offset(self):
        absensi = self._make_absensi(date(2026, 7, 5), time(8, 0), timedelta(hours=8))
        self.assertEqual(absensi.jam_keluar, time(16, 0))
        self.assertEqual(absensi.keluar_hari_offset, 0)

    def test_cross_midnight_keluar_has_plus_one_offset(self):
        absensi = self._make_absensi(date(2026, 7, 5), time(22, 0), timedelta(hours=8))
        self.assertEqual(absensi.jam_keluar, time(6, 0))
        self.assertEqual(absensi.keluar_hari_offset, 1)

    def test_cross_midnight_end_is_after_shift_end_same_clock_time(self):
        tanggal = date(2026, 7, 5)

        class Shift:
            jam_masuk = time(8, 0)
            jam_keluar = time(16, 0)

        absensi = self._make_absensi(tanggal, time(22, 0), timedelta(hours=8))
        self.assertGreaterEqual(
            _absensi_end_datetime(absensi),
            _shift_end_datetime(tanggal, Shift()),
        )
