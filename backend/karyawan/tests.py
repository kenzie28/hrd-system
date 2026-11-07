from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from karyawan.models import Karyawan
from karyawan.services import import_base_gaji_csv


class BaseGajiCsvImportTests(TestCase):
    def setUp(self):
        self.staff_a = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            jabatan='Staff',
            level=1,
            base_gaji=1,
        )
        self.staff_b = Karyawan.objects.create(
            karyawan_id='1000002',
            nama='Ani',
            jabatan='Staff',
            level=1,
            base_gaji=1,
        )
        self.senior = Karyawan.objects.create(
            karyawan_id='1000003',
            nama='Citra',
            jabatan='Staff Senior',
            level=2,
            base_gaji=9,
        )

    def _upload(self, body: str):
        upload = SimpleUploadedFile(
            'base-gaji.csv',
            body.encode(),
            content_type='text/csv',
        )
        return import_base_gaji_csv(upload)

    def test_exact_jabatan_updates_every_matching_employee(self):
        result = self._upload(
            'jabatan,base_gaji\n'
            'Staff,4500000\n'
            'Staff Senior,8000000\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.updated, 3)
        self.staff_a.refresh_from_db()
        self.staff_b.refresh_from_db()
        self.senior.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 4_500_000)
        self.assertEqual(self.staff_b.base_gaji, 4_500_000)
        self.assertEqual(self.senior.base_gaji, 8_000_000)

    def test_case_and_unknown_jabatan_write_nothing(self):
        unknown = self._upload(
            'jabatan,base_gaji\n'
            'staff,100\n'
            'Staff,200\n'
        )
        self.assertFalse(unknown.ok)
        self.assertIn('tidak ditemukan', unknown.errors[0].message)
        self.staff_a.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 1)

        missing = self._upload(
            'jabatan;base_gaji\n'
            'Direktur;100\n'
        )
        self.assertFalse(missing.ok)
        self.assertIn('Direktur', missing.errors[0].message)
        self.staff_a.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 1)

    def test_bad_nominal_and_duplicate_jabatan_write_nothing(self):
        negative = self._upload(
            'jabatan,base_gaji\n'
            'Staff,-1\n'
        )
        self.assertFalse(negative.ok)
        self.assertIn('tidak valid', negative.errors[0].message)

        duplicate = self._upload(
            'jabatan,base_gaji\n'
            'Staff,10\n'
            'Staff,20\n'
        )
        self.assertFalse(duplicate.ok)
        self.assertIn('duplikat', duplicate.errors[0].message)
        self.staff_a.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 1)

    def test_strips_surrounding_space_but_keeps_internal_space(self):
        result = self._upload(
            'jabatan,base_gaji\n'
            ' Staff ,0\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.staff_a.refresh_from_db()
        self.senior.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 0)
        self.assertEqual(self.senior.base_gaji, 9)


class AdminBaseGajiImportApiTests(TestCase):
    def setUp(self):
        self.admin = Karyawan.objects.create(
            karyawan_id='0000003',
            nama='Admin',
            jabatan='Director',
            level=8,
        )
        self.admin.refresh_from_db()
        Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            jabatan='Staff',
            level=1,
        )
        self.client = APIClient()
        token = Token.objects.create(user=self.admin.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_import_sets_base_gaji(self):
        upload = SimpleUploadedFile(
            'base-gaji.csv',
            b'jabatan,base_gaji\nStaff,1500000\n',
            content_type='text/csv',
        )
        response = self.client.post(
            '/api/admin/karyawan/import-base-gaji/',
            {'file': upload},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['ok'])
        self.assertEqual(response.data['updated'], 1)
        self.assertEqual(
            Karyawan.objects.get(pk='1000001').base_gaji,
            1_500_000,
        )
        self.assertEqual(Karyawan.objects.get(pk='0000003').base_gaji, 0)
