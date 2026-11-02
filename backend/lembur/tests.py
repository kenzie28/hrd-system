from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from lembur.services import import_lembur_csv


class LemburCsvImportTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
        )

    def _upload(self, rows: str, header='karyawan_id,tanggal'):
        upload = SimpleUploadedFile(
            'lembur.csv',
            f'{header}\n{rows}'.encode(),
            content_type='text/csv',
        )
        return import_lembur_csv(upload)

    def test_creates_approved_requests_and_skips_duplicates(self):
        result = self._upload(
            '1000001,2026-11-02\n1000001,2026-11-02\n1000001,2026-11-03\n'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.created, 2)
        requests = PermohonanLembur.objects.order_by('tanggal')
        self.assertEqual(
            list(requests.values_list('tanggal', flat=True)),
            [date(2026, 11, 2), date(2026, 11, 3)],
        )
        self.assertTrue(
            all(
                request.status == StatusPermohonanLembur.APPROVED
                and request.karyawan_id == self.employee.pk
                and request.supervisor_id is None
                and request.hrd_approver_id is None
                for request in requests
            )
        )

        again = import_lembur_csv(
            SimpleUploadedFile(
                'lembur.csv',
                'karyawan_id;tanggal\n1000001;2026-11-03\n'.encode(),
                content_type='text/csv',
            )
        )
        self.assertTrue(again.ok)
        self.assertEqual(again.created, 0)
        self.assertEqual(PermohonanLembur.objects.count(), 2)

    def test_unknown_employee_writes_nothing(self):
        result = self._upload('9999999,2026-11-02\n1000001,2026-11-03\n')

        self.assertFalse(result.ok)
        self.assertIn('tidak ditemukan', result.errors[0].message)
        self.assertEqual(PermohonanLembur.objects.count(), 0)

    def test_invalid_date_writes_nothing(self):
        result = self._upload('1000001,02-11-2026\n')

        self.assertFalse(result.ok)
        self.assertIn('yyyy-mm-dd', result.errors[0].message)
        self.assertEqual(PermohonanLembur.objects.count(), 0)

    def test_missing_column(self):
        result = self._upload('1000001\n', header='karyawan_id')

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].row, 0)
        self.assertIn('tanggal', result.errors[0].message)
