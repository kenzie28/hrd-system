from datetime import date
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from absensi.models import PendingAttendanceDay, RekapAbsensi
from absensi.services import import_absensi_csv
from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from cuti.services import approve_by_hrd, approve_cancellation_by_hrd
from karyawan.models import Karyawan
from karyawan.services import import_karyawan_update_csv
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from lembur.services import approve_by_hrd as approve_lembur
from liburan.services import import_liburan_csv
from lokasi.models import Lokasi
from shift.services import import_shift_csv
from state_manager.constants import TABLE_ABSENSI
from state_manager.services import clear_state_tables


class BulkCorridorInvalidationTests(TestCase):
    def setUp(self):
        self.old_location = Lokasi.objects.create(id='80', nama='Old')
        self.new_location = Lokasi.objects.create(id='81', nama='New')
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            lokasi_kerja=self.old_location,
            level=1,
            cuti_tahunan=10,
        )
        PendingAttendanceDay.objects.all().delete()

    def _upload(self, name, text):
        return SimpleUploadedFile(name, text.encode(), content_type='text/csv')

    def assert_one_drain(self, callbacks):
        self.assertEqual(len(callbacks), 1)

    def test_absensi_csv_enqueues_created_days_once(self):
        upload = self._upload(
            'absensi.csv',
            'karyawan_id,lokasi_kerja,tanggal,jam_masuk,jam_keluar\n'
            '1000001,80,2026-09-01,08:00,17:00\n'
            '1000001,80,2026-09-02,08:00,17:00\n',
        )
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            result = import_absensi_csv(upload)

        self.assertTrue(result.ok, result.errors)
        self.assert_one_drain(callbacks)
        self.assertEqual(
            set(PendingAttendanceDay.objects.values_list('karyawan_id', 'tanggal')),
            {
                ('1000001', date(2026, 9, 1)),
                ('1000001', date(2026, 9, 2)),
            },
        )

    def test_shift_and_holiday_csv_expand_bulk_sources(self):
        RekapAbsensi.objects.create(
            karyawan=self.employee, month=date(2026, 9, 1)
        )
        shift_upload = self._upload(
            'shift.csv',
            'lokasi_kerja,hari,jam_masuk,jam_keluar\n'
            '80,Selasa,08:00,17:00\n',
        )
        with self.captureOnCommitCallbacks(execute=False) as shift_callbacks:
            shift_result = import_shift_csv(shift_upload)
        self.assertTrue(shift_result.ok, shift_result.errors)
        self.assert_one_drain(shift_callbacks)
        self.assertTrue(
            PendingAttendanceDay.objects.filter(
                karyawan=self.employee, tanggal=date(2026, 9, 1)
            ).exists()
        )

        PendingAttendanceDay.objects.all().delete()
        holiday_upload = self._upload(
            'liburan.csv',
            'nama,tanggal\nHari Libur,2026-09-03\n',
        )
        with self.captureOnCommitCallbacks(execute=False) as holiday_callbacks:
            holiday_result = import_liburan_csv(holiday_upload)
        self.assertTrue(holiday_result.ok, holiday_result.errors)
        self.assert_one_drain(holiday_callbacks)
        self.assertTrue(
            PendingAttendanceDay.objects.filter(
                karyawan=self.employee, tanggal=date(2026, 9, 3)
            ).exists()
        )

    def test_karyawan_bulk_location_change_enqueues_tracked_days_once(self):
        RekapAbsensi.objects.create(
            karyawan=self.employee, month=date(2026, 9, 1)
        )
        PendingAttendanceDay.objects.all().delete()
        upload = BytesIO(
            b'karyawan_id,lokasi_kerja\n1000001,81\n'
        )
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            result = import_karyawan_update_csv(upload)

        self.assertTrue(result.ok, result.errors)
        self.assert_one_drain(callbacks)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.lokasi_kerja_id, '81')
        self.assertTrue(
            PendingAttendanceDay.objects.filter(
                karyawan=self.employee, tanggal=date(2026, 9, 1)
            ).exists()
        )

    def test_cuti_bulk_replace_and_cancel_each_schedule_one_drain(self):
        request = PermohonanCuti.objects.create(
            karyawan=self.employee,
            tipe=TipeCuti.TAHUNAN,
            tanggal_mulai=date(2026, 9, 1),
            tanggal_selesai=date(2026, 9, 2),
            status=StatusPermohonanCuti.MENUNGGU_HRD,
        )
        Cuti.objects.create(permohonan=request, tanggal=date(2026, 8, 31))
        PendingAttendanceDay.objects.all().delete()

        with self.captureOnCommitCallbacks(execute=False) as approve_callbacks:
            approve_by_hrd(request, None)
        self.assert_one_drain(approve_callbacks)
        self.assertEqual(
            set(
                PendingAttendanceDay.objects.filter(
                    karyawan=self.employee
                ).values_list('tanggal', flat=True)
            ),
            {
                date(2026, 8, 31),
                date(2026, 9, 1),
                date(2026, 9, 2),
            },
        )

        PendingAttendanceDay.objects.all().delete()
        with self.captureOnCommitCallbacks(execute=False) as cancel_callbacks:
            approve_cancellation_by_hrd(request)
        self.assert_one_drain(cancel_callbacks)
        self.assertEqual(
            set(PendingAttendanceDay.objects.values_list('tanggal', flat=True)),
            {date(2026, 9, 1), date(2026, 9, 2)},
        )

    def test_lembur_status_and_state_clear_enqueue_once(self):
        overtime = PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 9, 1),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        PendingAttendanceDay.objects.all().delete()
        with self.captureOnCommitCallbacks(execute=False) as lembur_callbacks:
            approve_lembur(overtime, None)
        self.assert_one_drain(lembur_callbacks)
        self.assertTrue(
            PendingAttendanceDay.objects.filter(
                karyawan=self.employee, tanggal=date(2026, 9, 1)
            ).exists()
        )

        PendingAttendanceDay.objects.all().delete()
        upload = self._upload(
            'absensi.csv',
            'karyawan_id,lokasi_kerja,tanggal,jam_masuk,jam_keluar\n'
            '1000001,80,2026-09-02,08:00,17:00\n',
        )
        import_absensi_csv(upload)
        PendingAttendanceDay.objects.all().delete()
        with self.captureOnCommitCallbacks(execute=False) as clear_callbacks:
            clear_state_tables([TABLE_ABSENSI])
        self.assert_one_drain(clear_callbacks)
        self.assertTrue(
            PendingAttendanceDay.objects.filter(
                karyawan=self.employee, tanggal=date(2026, 9, 2)
            ).exists()
        )
