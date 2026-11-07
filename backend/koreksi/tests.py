from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from karyawan.models import Karyawan
from koreksi.models import Koreksi, TipeKoreksi
from koreksi.services import import_koreksi_csv


class KoreksiCsvImportTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
        )

    def _upload(self, body: str, filename='koreksi.csv'):
        upload = SimpleUploadedFile(
            filename,
            body.encode(),
            content_type='text/csv',
        )
        return import_koreksi_csv(upload)

    def test_inserts_both_types_and_a_second_upload_duplicates_rows(self):
        body = (
            'karyawan_id,tipe,nominal,bulan\n'
            '1000001,Koreksi Admin,-50000,2026-11\n'
            '1000001,Koreksi Absensi,3000000000,202611\n'
            "1000001,Koreksi Admin,-50000,2026-11-15\n"
        )
        result = self._upload(body)

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.created, 3)
        rows = list(Koreksi.objects.order_by('id'))
        self.assertEqual(
            [(row.tipe, row.nominal, row.bulan) for row in rows],
            [
                (TipeKoreksi.ADMIN, -50000, date(2026, 11, 1)),
                (TipeKoreksi.ABSENSI, 3_000_000_000, date(2026, 11, 1)),
                (TipeKoreksi.ADMIN, -50000, date(2026, 11, 1)),
            ],
        )

        again = self._upload(
            'karyawan_id;tipe;nominal;bulan\n'
            '1000001;Koreksi Absensi;125000;2026-11-01\n'
        )
        self.assertTrue(again.ok, again.errors)
        self.assertEqual(again.created, 1)
        self.assertEqual(Koreksi.objects.count(), 4)
        self.assertEqual(
            Koreksi.objects.filter(tipe=TipeKoreksi.ABSENSI).count(),
            2,
        )

    def test_unknown_karyawan_bad_tipe_and_bad_nominal_write_nothing(self):
        unknown = self._upload(
            'karyawan_id,tipe,nominal,bulan\n'
            '9999999,Koreksi Admin,-1,2026-11\n'
            '1000001,Koreksi Admin,-2,2026-11\n'
        )
        self.assertFalse(unknown.ok)
        self.assertIn('tidak ditemukan', unknown.errors[0].message)
        self.assertEqual(Koreksi.objects.count(), 0)

        bad_tipe = self._upload(
            'karyawan_id,tipe,nominal,bulan\n'
            '1000001,Admin,-1,2026-11\n'
        )
        self.assertFalse(bad_tipe.ok)
        self.assertIn('Koreksi Admin', bad_tipe.errors[0].message)
        self.assertEqual(Koreksi.objects.count(), 0)

        bad_nominal = self._upload(
            'karyawan_id,tipe,nominal,bulan\n'
            '1000001,Koreksi Absensi,"1,000",2026-11-01\n'
        )
        self.assertFalse(bad_nominal.ok)
        self.assertIn('Nominal tidak valid', bad_nominal.errors[0].message)
        self.assertEqual(Koreksi.objects.count(), 0)

        overflow = self._upload(
            'karyawan_id,tipe,nominal,bulan\n'
            '1000001,Koreksi Absensi,9223372036854775808,2026-11\n'
        )
        self.assertFalse(overflow.ok)
        self.assertIn('batas', overflow.errors[0].message)
        self.assertEqual(Koreksi.objects.count(), 0)

    def test_pads_karyawan_id_and_strips_excel_quote(self):
        Karyawan.objects.create(karyawan_id='0000001', nama='Ani', level=1)
        result = self._upload(
            'karyawan_id,tipe,nominal,bulan\n'
            "'1,Koreksi Admin,10,2026-02-01\n"
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(Koreksi.objects.get().karyawan_id, '0000001')


class AdminKoreksiApiTests(TestCase):
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

    def test_import_lists_labels_for_the_selected_month(self):
        upload = SimpleUploadedFile(
            'koreksi.csv',
            (
                'karyawan_id,tipe,nominal,bulan\n'
                '1000001,Koreksi Admin,-50000,2026-11-01\n'
                '1000001,Koreksi Absensi,125000,2026-10\n'
            ).encode(),
            content_type='text/csv',
        )
        response = self.client.post(
            '/api/admin/koreksi/import/',
            {'file': upload},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['ok'])
        self.assertEqual(response.data['created'], 2)

        listed = self.client.get('/api/admin/koreksi/', {'bulan': '2026-11'})
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]['tipe'], 'Koreksi Admin')
        self.assertEqual(listed.data[0]['nominal'], -50000)
        self.assertEqual(listed.data[0]['karyawan_nama'], 'Budi')
        self.assertEqual(listed.data[0]['bulan'], '2026-11-01')
