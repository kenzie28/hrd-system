from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from absensi.models import Kehadiran, StatusKehadiran
from karyawan.models import Karyawan
from lokasi.models import Lokasi
from shift.models import HariKerja, Shift


class ShiftDeleteTests(TestCase):
    def test_delete_unlinks_kehadiran_instead_of_blocking(self):
        lokasi = Lokasi.objects.create(id='81', nama='Toko 81')
        karyawan = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            lokasi_kerja=lokasi,
            level=1,
        )
        shift = Shift.objects.create(
            lokasi_kerja=lokasi,
            hari=HariKerja.SELASA,
            jam_masuk=time(8, 0),
            jam_keluar=time(17, 0),
        )
        kehadiran = Kehadiran.objects.create(
            karyawan=karyawan,
            tanggal=date(2026, 9, 1),
            shift=shift,
            status=StatusKehadiran.HADIR,
        )

        response = APIClient().delete(f'/api/shifts/{shift.pk}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Shift.objects.filter(pk=shift.pk).exists())
        kehadiran.refresh_from_db()
        self.assertIsNone(kehadiran.shift_id)
        self.assertEqual(kehadiran.status, StatusKehadiran.HADIR)
