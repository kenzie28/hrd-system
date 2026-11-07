from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from karyawan.models import Karyawan
from obat.models import TunjanganObat
from obat.services import import_tunjangan_obat_csv


class TunjanganObatCsvImportTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
        )

    def _upload(self, body: str, filename='tunjangan-obat.csv'):
        upload = SimpleUploadedFile(
            filename,
            body.encode(),
            content_type='text/csv',
        )
        return import_tunjangan_obat_csv(upload)

    def test_inserts_rows_and_a_second_upload_duplicates_them(self):
        body = (
            'karyawan_id,nominal,bulan\n'
            '1000001,150000,2026-11\n'
            '1000001,3000000000,202611\n'
            '1000001,0,2026-11-15\n'
        )
        result = self._upload(body)

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.created, 3)
        rows = list(TunjanganObat.objects.order_by('id'))
        self.assertEqual(
            [(row.nominal, row.bulan) for row in rows],
            [
                (150_000, date(2026, 11, 1)),
                (3_000_000_000, date(2026, 11, 1)),
                (0, date(2026, 11, 1)),
            ],
        )

        again = self._upload(
            'karyawan_id;nominal;bulan\n'
            '1000001;125000;2026-11-01\n'
        )
        self.assertTrue(again.ok, again.errors)
        self.assertEqual(again.created, 1)
        self.assertEqual(TunjanganObat.objects.count(), 4)

    def test_unknown_karyawan_and_bad_nominal_write_nothing(self):
        unknown = self._upload(
            'karyawan_id,nominal,bulan\n'
            '9999999,1,2026-11\n'
            '1000001,2,2026-11\n'
        )
        self.assertFalse(unknown.ok)
        self.assertIn('tidak ditemukan', unknown.errors[0].message)
        self.assertEqual(TunjanganObat.objects.count(), 0)

        negative = self._upload(
            'karyawan_id,nominal,bulan\n'
            '1000001,-1,2026-11\n'
        )
        self.assertFalse(negative.ok)
        self.assertIn('Nominal tidak valid', negative.errors[0].message)
        self.assertEqual(TunjanganObat.objects.count(), 0)

        bad_nominal = self._upload(
            'karyawan_id,nominal,bulan\n'
            '1000001,"1,000",2026-11-01\n'
        )
        self.assertFalse(bad_nominal.ok)
        self.assertIn('Nominal tidak valid', bad_nominal.errors[0].message)
        self.assertEqual(TunjanganObat.objects.count(), 0)

        overflow = self._upload(
            'karyawan_id,nominal,bulan\n'
            '1000001,9223372036854775808,2026-11\n'
        )
        self.assertFalse(overflow.ok)
        self.assertIn('batas', overflow.errors[0].message)
        self.assertEqual(TunjanganObat.objects.count(), 0)

    def test_pads_karyawan_id_and_strips_excel_quote(self):
        Karyawan.objects.create(karyawan_id='0000001', nama='Ani', level=1)
        result = self._upload(
            'karyawan_id,nominal,bulan\n'
            "'1,10,2026-02-01\n"
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(TunjanganObat.objects.get().karyawan_id, '0000001')


class AdminTunjanganObatApiTests(TestCase):
    def setUp(self):
        self.admin = Karyawan.objects.create(
            karyawan_id='0000003',
            nama='Admin',
            level=8,
        )
        self.admin.refresh_from_db()
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
        )
        self.client = APIClient()
        token = Token.objects.create(user=self.admin.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_import_lists_rows_for_the_selected_month(self):
        upload = SimpleUploadedFile(
            'tunjangan-obat.csv',
            (
                'karyawan_id,nominal,bulan\n'
                '1000001,150000,2026-11-01\n'
                '1000001,125000,2026-10\n'
            ).encode(),
            content_type='text/csv',
        )
        response = self.client.post(
            '/api/admin/tunjangan-obat/import/',
            {'file': upload},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['ok'])
        self.assertEqual(response.data['created'], 2)

        listed = self.client.get('/api/admin/tunjangan-obat/', {'bulan': '2026-11'})
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]['nominal'], 150000)
        self.assertEqual(listed.data[0]['karyawan_nama'], 'Budi')
        self.assertEqual(listed.data[0]['bulan'], '2026-11-01')
