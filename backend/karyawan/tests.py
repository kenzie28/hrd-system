from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from gaji.access import GAJI_PASSWORD
from karyawan.models import Karyawan
from karyawan.serializers import KaryawanSerializer
from karyawan.services import (
    import_base_gaji_csv,
    import_gaji_bulanan_csv,
    import_karyawan_update_csv,
    import_karyawan_upsert_csv,
)
from lokasi.models import Lokasi


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
        self.token = Token.objects.create(user=self.admin.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
            HTTP_X_GAJI_PASSWORD=GAJI_PASSWORD,
        )

    def test_import_rejects_missing_gaji_password(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        upload = SimpleUploadedFile(
            'base-gaji.csv',
            b'karyawan_id,base_gaji\n1000001,1500000\n',
            content_type='text/csv',
        )
        response = client.post(
            '/api/admin/gaji/import-base-gaji/',
            {'file': upload},
            format='multipart',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Karyawan.objects.get(pk='1000001').base_gaji, 0)

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


class KaryawanUpdateStatusCsvTests(TestCase):
    def setUp(self):
        self.staff = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
            status_k_tk='TK',
            base_gaji=4_500_000,
            gaji_bulanan=6_000_000,
        )
        self.other = Karyawan.objects.create(
            karyawan_id='1000002',
            nama='Ani',
            level=1,
            status_k_tk='K0',
        )
        self.client = APIClient()

    def _upload(self, body: str):
        upload = SimpleUploadedFile(
            'update-karyawan.csv',
            body.encode(),
            content_type='text/csv',
        )
        return import_karyawan_update_csv(upload)

    def test_updates_status_k_tk_for_that_employee_only(self):
        result = self._upload('karyawan_id,status_k_tk\n1000001,k2\n')
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.updated, 1)
        self.staff.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.staff.status_k_tk, 'K2')
        self.assertEqual(self.other.status_k_tk, 'K0')
        self.assertEqual(self.staff.base_gaji, 4_500_000)
        self.assertEqual(self.staff.gaji_bulanan, 6_000_000)

    def test_blank_status_clears_the_field(self):
        result = self._upload('karyawan_id,status_k_tk\n1000001,\n')
        self.assertTrue(result.ok, result.errors)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.status_k_tk, '')

    def test_invalid_status_writes_nothing(self):
        result = self._upload('karyawan_id,status_k_tk\n1000001,KAWIN\n')
        self.assertFalse(result.ok)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.status_k_tk, 'TK')

    def test_updates_npwp_no_bpjs_and_no_kpj(self):
        self.other.npwp = 'keep-me'
        self.other.no_bpjs = '111'
        self.other.no_kpj = '222'
        self.other.save(update_fields=['npwp', 'no_bpjs', 'no_kpj'])

        result = self._upload(
            'karyawan_id,npwp,no_bpjs,no_kpj\n'
            '1000001,55.042.174.7-044.000,0001234567890,10000740943\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.updated, 1)
        self.assertIn('npwp', result.optional_columns)
        self.assertIn('no_bpjs', result.optional_columns)
        self.assertIn('no_kpj', result.optional_columns)
        self.staff.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.staff.npwp, '55.042.174.7-044.000')
        self.assertEqual(self.staff.no_bpjs, '0001234567890')
        self.assertEqual(self.staff.no_kpj, '10000740943')
        self.assertEqual(self.staff.base_gaji, 4_500_000)
        self.assertEqual(self.other.npwp, 'keep-me')
        self.assertEqual(self.other.no_bpjs, '111')
        self.assertEqual(self.other.no_kpj, '222')

    def test_blank_identity_numbers_clear_the_fields(self):
        self.staff.npwp = '55.042.174.7-044.000'
        self.staff.no_bpjs = '0001234567890'
        self.staff.no_kpj = '10000740943'
        self.staff.save(update_fields=['npwp', 'no_bpjs', 'no_kpj'])

        result = self._upload('karyawan_id,npwp,no_bpjs,no_kpj\n1000001,,,\n')
        self.assertTrue(result.ok, result.errors)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.npwp, '')
        self.assertEqual(self.staff.no_bpjs, '')
        self.assertEqual(self.staff.no_kpj, '')

    def test_updates_tanggal_lahir(self):
        self.other.tanggal_lahir = date(1990, 1, 2)
        self.other.save(update_fields=['tanggal_lahir'])

        result = self._upload(
            'karyawan_id,tanggal_lahir\n1000001,24/12/1974\n'
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.updated, 1)
        self.assertIn('tanggal_lahir', result.optional_columns)
        self.staff.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.staff.tanggal_lahir, date(1974, 12, 24))
        self.assertEqual(self.staff.base_gaji, 4_500_000)
        self.assertEqual(self.other.tanggal_lahir, date(1990, 1, 2))

    def test_blank_tanggal_lahir_clears_the_field(self):
        self.staff.tanggal_lahir = date(1974, 12, 24)
        self.staff.save(update_fields=['tanggal_lahir'])

        result = self._upload('karyawan_id,tanggal_lahir\n1000001,\n')
        self.assertTrue(result.ok, result.errors)
        self.staff.refresh_from_db()
        self.assertIsNone(self.staff.tanggal_lahir)

    def test_invalid_tanggal_lahir_writes_nothing(self):
        self.staff.tanggal_lahir = date(1974, 12, 24)
        self.staff.save(update_fields=['tanggal_lahir'])

        result = self._upload('karyawan_id,tanggal_lahir\n1000001,bukan-tanggal\n')
        self.assertFalse(result.ok)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.tanggal_lahir, date(1974, 12, 24))

    def test_overlong_identity_number_writes_nothing(self):
        self.staff.no_bpjs = '0001234567890'
        self.staff.no_kpj = '10000740943'
        self.staff.save(update_fields=['no_bpjs', 'no_kpj'])

        result = self._upload(
            'karyawan_id,no_bpjs,no_kpj\n1000001,' + ('1' * 17) + ',10000740943\n'
        )
        self.assertFalse(result.ok)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.no_bpjs, '0001234567890')
        self.assertEqual(self.staff.no_kpj, '10000740943')

    def test_list_api_omits_wage_fields(self):
        response = self.client.get('/api/karyawan/')
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data if item['karyawan_id'] == '1000001')
        self.assertEqual(row['status_k_tk'], 'TK')
        self.assertNotIn('base_gaji', row)
        self.assertNotIn('gaji_bulanan', row)
        self.assertNotIn('absensi_dihitung', row)
        self.assertNotIn('lembur_dibayar', row)
        self.assertNotIn('jumlah_anak', row)
        self.assertNotIn('nikah', row)


class KaryawanActiveTests(TestCase):
    def test_active_through_exit_date(self):
        today = timezone.localdate()
        staying = Karyawan.objects.create(
            karyawan_id='1000001', nama='Budi', level=1
        )
        leaving_today = Karyawan.objects.create(
            karyawan_id='1000002',
            nama='Ani',
            level=1,
            tanggal_keluar=today,
        )
        left = Karyawan.objects.create(
            karyawan_id='1000003',
            nama='Citra',
            level=1,
            tanggal_keluar=today - timedelta(days=1),
        )

        self.assertTrue(staying.active)
        self.assertTrue(leaving_today.active)
        self.assertFalse(left.active)

    def test_umur_and_lama_kerja_count_completed_years(self):
        today = timezone.localdate()
        person = Karyawan(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
            tanggal_lahir=_years_before(today, 30),
            tanggal_awal=_years_before(today, 8),
        )
        self.assertEqual(person.umur, 30)
        self.assertEqual(person.lama_kerja, 8)

        person.tanggal_lahir = _years_before(today + timedelta(days=1), 30)
        self.assertEqual(person.umur, 29)

    def test_lama_kerja_stops_on_exit_and_is_empty_without_a_start(self):
        today = timezone.localdate()
        person = Karyawan(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
            tanggal_awal=_years_before(today, 10),
            tanggal_keluar=_years_before(today, 2),
        )
        self.assertEqual(person.lama_kerja, 8)
        person.tanggal_awal = None
        person.tanggal_lahir = None
        self.assertIsNone(person.lama_kerja)
        self.assertIsNone(person.umur)


class KaryawanUpsertCsvTests(TestCase):
    def test_upsert_leaves_absensi_dihitung_unchanged(self):
        Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
            absensi_dihitung=False,
            base_gaji=12_345,
            gaji_bulanan=67_890,
            lembur_dibayar=True,
        )
        result = import_karyawan_upsert_csv(
            SimpleUploadedFile(
                'mini.csv',
                b'karyawan_id,nama,level\n1000001,Budi Baru,2\n1000002,Ani,1\n',
                content_type='text/csv',
            )
        )
        self.assertTrue(result.ok, result.errors)
        budi = Karyawan.objects.get(pk='1000001')
        self.assertEqual(budi.nama, 'Budi Baru')
        self.assertEqual(budi.level, 2)
        self.assertFalse(budi.absensi_dihitung)
        self.assertEqual(budi.base_gaji, 12_345)
        self.assertEqual(budi.gaji_bulanan, 67_890)
        self.assertTrue(budi.lembur_dibayar)
        ani = Karyawan.objects.get(pk='1000002')
        self.assertTrue(ani.absensi_dihitung)
        self.assertFalse(ani.lembur_dibayar)

    def test_ho_file_creates_then_updates_without_clearing_wages(self):
        Lokasi.objects.create(id='99', nama='Headquarters')
        payload = (Path(settings.BASE_DIR).parent / 'HO Employee Data.csv').read_bytes()

        created = import_karyawan_upsert_csv(
            SimpleUploadedFile('HO Employee Data.csv', payload, content_type='text/csv')
        )
        self.assertTrue(created.ok, created.errors)
        self.assertEqual(created.created, 87)
        self.assertEqual(created.updated, 0)
        self.assertEqual(created.errors, [])
        self.assertEqual(Karyawan.objects.count(), 87)
        self.assertEqual(User.objects.count(), 87)

        suparni = Karyawan.objects.get(pk='9400143')
        self.assertEqual(suparni.nama, 'SUPARNI')
        self.assertEqual(suparni.level, 2)
        self.assertEqual(suparni.jabatan, 'Adm F Penj Jr')
        self.assertEqual(suparni.status_kontrak, 'A9')
        self.assertFalse(suparni.percobaan_jabatan)
        self.assertEqual(suparni.tanggal_kontrak_awal, date(1994, 11, 24))
        self.assertIsNone(suparni.tanggal_kontrak_akhir)
        self.assertEqual(suparni.tanggal_awal, date(1994, 11, 24))
        self.assertEqual(suparni.tanggal_lahir, date(1974, 12, 24))
        self.assertEqual(suparni.jenis_kelamin, 'Perempuan')
        self.assertEqual(suparni.status_k_tk, 'K1')
        self.assertEqual(suparni.lokasi_kerja_id, '80')
        self.assertEqual(suparni.npwp, '55.042.174.7-044.000')
        self.assertEqual(suparni.no_bpjs, '')
        self.assertEqual(suparni.no_kpj, '10000740943')
        self.assertEqual(suparni.tanggal_kpj, date(2010, 1, 1))
        self.assertIsNotNone(suparni.user_id)
        serialized = KaryawanSerializer(suparni).data
        self.assertEqual(serialized['jenis_kelamin'], 'Perempuan')
        self.assertEqual(serialized['tanggal_lahir'], '1974-12-24')
        self.assertEqual(serialized['npwp'], '55.042.174.7-044.000')
        self.assertEqual(serialized['no_bpjs'], '')
        self.assertEqual(serialized['no_kpj'], '10000740943')
        self.assertNotIn('base_gaji', serialized)
        self.assertNotIn('gaji_bulanan', serialized)
        self.assertNotIn('absensi_dihitung', serialized)
        self.assertNotIn('lembur_dibayar', serialized)

        wah = Karyawan.objects.get(pk='2406021')
        self.assertIsNone(wah.tanggal_lahir)
        self.assertIsNone(wah.tanggal_kontrak_akhir)
        self.assertIsNone(wah.tanggal_kpj)
        self.assertEqual(wah.jenis_kelamin, 'Laki-Laki')

        self.assertEqual(Karyawan.objects.get(pk='2508001').level, 0)
        self.assertEqual(Karyawan.objects.get(pk='0000002').level, 9)
        self.assertEqual(Karyawan.objects.get(pk='1604021').npwp, '99')
        self.assertEqual(Karyawan.objects.get(pk='2610001').lokasi_kerja_id, '81')
        self.assertEqual(Lokasi.objects.get(pk='80').nama, '80')
        self.assertEqual(Lokasi.objects.get(pk='81').nama, '81')
        self.assertEqual(Lokasi.objects.get(pk='99').nama, 'Headquarters')

        suparni.base_gaji = 12_345
        suparni.gaji_bulanan = 67_890
        suparni.absensi_dihitung = False
        suparni.lembur_dibayar = True
        suparni.cuti_tahunan = 3
        suparni.wilayah = 'BDG'
        suparni.save(
            update_fields=[
                'base_gaji',
                'gaji_bulanan',
                'absensi_dihitung',
                'lembur_dibayar',
                'cuti_tahunan',
                'wilayah',
            ]
        )
        user_id = suparni.user_id

        updated = import_karyawan_upsert_csv(
            SimpleUploadedFile('HO Employee Data.csv', payload, content_type='text/csv')
        )
        self.assertTrue(updated.ok, updated.errors)
        self.assertEqual(updated.created, 0)
        self.assertEqual(updated.updated, 87)
        self.assertEqual(Karyawan.objects.count(), 87)
        self.assertEqual(User.objects.count(), 87)

        suparni.refresh_from_db()
        self.assertEqual(suparni.base_gaji, 12_345)
        self.assertEqual(suparni.gaji_bulanan, 67_890)
        self.assertFalse(suparni.absensi_dihitung)
        self.assertTrue(suparni.lembur_dibayar)
        self.assertEqual(suparni.cuti_tahunan, 3)
        self.assertEqual(suparni.wilayah, 'BDG')
        self.assertEqual(suparni.user_id, user_id)
        self.assertEqual(suparni.nama, 'SUPARNI')
        self.assertEqual(Lokasi.objects.get(pk='99').nama, 'Headquarters')


def _years_before(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)
