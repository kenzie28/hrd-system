from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from karyawan.models import Karyawan
from karyawan.services import import_base_gaji_csv, import_gaji_bulanan_csv


class KaryawanWageCsvImportTests(TestCase):
    def setUp(self):
        self.staff_a = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            jabatan='Staff',
            level=1,
            base_gaji=1,
            gaji_bulanan=1,
        )
        self.staff_b = Karyawan.objects.create(
            karyawan_id='1000002',
            nama='Ani',
            jabatan='Staff',
            level=1,
            base_gaji=1,
            gaji_bulanan=1,
        )
        self.senior = Karyawan.objects.create(
            karyawan_id='1000003',
            nama='Citra',
            jabatan='Staff Senior',
            level=2,
            base_gaji=9,
            gaji_bulanan=9,
        )

    def _upload_base(self, body: str):
        upload = SimpleUploadedFile(
            'base-gaji.csv',
            body.encode(),
            content_type='text/csv',
        )
        return import_base_gaji_csv(upload)

    def _upload_bulanan(self, body: str):
        upload = SimpleUploadedFile(
            'gaji-bulanan.csv',
            body.encode(),
            content_type='text/csv',
        )
        return import_gaji_bulanan_csv(upload)

    def test_each_karyawan_id_updates_only_that_employee(self):
        result = self._upload_base(
            'karyawan_id,base_gaji\n'
            '1000001,4500000\n'
            '1000003,8000000\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.updated, 2)
        self.staff_a.refresh_from_db()
        self.staff_b.refresh_from_db()
        self.senior.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 4_500_000)
        self.assertEqual(self.staff_b.base_gaji, 1)
        self.assertEqual(self.senior.base_gaji, 8_000_000)

    def test_gaji_bulanan_updates_only_that_employee(self):
        result = self._upload_bulanan(
            'karyawan_id,gaji_bulanan\n'
            '1000002,3200000\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.updated, 1)
        self.staff_a.refresh_from_db()
        self.staff_b.refresh_from_db()
        self.assertEqual(self.staff_a.gaji_bulanan, 1)
        self.assertEqual(self.staff_b.gaji_bulanan, 3_200_000)
        self.assertEqual(self.staff_b.base_gaji, 1)

    def test_unknown_karyawan_and_missing_column_write_nothing(self):
        unknown = self._upload_base(
            'karyawan_id,base_gaji\n'
            '9999999,100\n'
            '1000001,200\n'
        )
        self.assertFalse(unknown.ok)
        self.assertIn('tidak ditemukan', unknown.errors[0].message)
        self.staff_a.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 1)

        missing = self._upload_base(
            'karyawan_id;base_gaji\n'
            '9999999;100\n'
        )
        self.assertFalse(missing.ok)
        self.assertIn('9999999', missing.errors[0].message)
        self.staff_a.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 1)

    def test_bad_nominal_and_duplicate_id_write_nothing(self):
        negative = self._upload_base(
            'karyawan_id,base_gaji\n'
            '1000001,-1\n'
        )
        self.assertFalse(negative.ok)
        self.assertIn('tidak valid', negative.errors[0].message)

        duplicate = self._upload_bulanan(
            'karyawan_id,gaji_bulanan\n'
            '1000001,10\n'
            '1000001,20\n'
        )
        self.assertFalse(duplicate.ok)
        self.assertIn('duplikat', duplicate.errors[0].message)
        self.staff_a.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 1)
        self.assertEqual(self.staff_a.gaji_bulanan, 1)

    def test_strips_space_and_leading_apostrophe(self):
        result = self._upload_base(
            'karyawan_id,base_gaji\n'
            ' 1000001 ,\'0\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.staff_a.refresh_from_db()
        self.senior.refresh_from_db()
        self.assertEqual(self.staff_a.base_gaji, 0)
        self.assertEqual(self.senior.base_gaji, 9)


class AdminWageImportApiTests(TestCase):
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
            b'karyawan_id,base_gaji\n1000001,1500000\n',
            content_type='text/csv',
        )
        response = self.client.post(
            '/api/admin/gaji/import-base-gaji/',
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

    def test_import_sets_gaji_bulanan(self):
        upload = SimpleUploadedFile(
            'gaji-bulanan.csv',
            b'karyawan_id,gaji_bulanan\n1000001,2750000\n',
            content_type='text/csv',
        )
        response = self.client.post(
            '/api/admin/gaji/import-gaji-bulanan/',
            {'file': upload},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['ok'])
        self.assertEqual(response.data['updated'], 1)
        self.assertEqual(
            Karyawan.objects.get(pk='1000001').gaji_bulanan,
            2_750_000,
        )
        self.assertEqual(Karyawan.objects.get(pk='0000003').gaji_bulanan, 0)
        self.assertEqual(Karyawan.objects.get(pk='1000001').base_gaji, 0)
