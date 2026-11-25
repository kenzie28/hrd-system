from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from dinas.models import Dinas
from dinas.services import import_dinas_csv
from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur


class DinasCsvImportTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
        )

    def _upload(self, rows: str, header='karyawan_id,tanggal'):
        upload = SimpleUploadedFile(
            'dinas.csv',
            f'{header}\n{rows}'.encode(),
            content_type='text/csv',
        )
        return import_dinas_csv(upload)

    def test_creates_dinas_and_skips_duplicates(self):
        result = self._upload(
            '1000001,2026-11-02\n1000001,2026-11-02\n1000001,2026-11-03\n'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.created, 2)
        self.assertEqual(
            list(Dinas.objects.order_by('tanggal').values_list('tanggal', flat=True)),
            [date(2026, 11, 2), date(2026, 11, 3)],
        )
        self.assertEqual(PermohonanLembur.objects.count(), 0)

        again = import_dinas_csv(
            SimpleUploadedFile(
                'dinas.csv',
                'karyawan_id;tanggal\n1000001;2026-11-03\n'.encode(),
                content_type='text/csv',
            )
        )
        self.assertTrue(again.ok)
        self.assertEqual(again.created, 0)
        self.assertEqual(Dinas.objects.count(), 2)

    def test_skips_a_day_that_already_has_approved_lembur(self):
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusPermohonanLembur.APPROVED,
        )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 4),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )

        result = self._upload('1000001,2026-11-02\n1000001,2026-11-04\n')

        self.assertTrue(result.ok)
        self.assertEqual(result.created, 1)
        self.assertFalse(Dinas.objects.filter(tanggal=date(2026, 11, 2)).exists())
        self.assertTrue(Dinas.objects.filter(tanggal=date(2026, 11, 4)).exists())
        self.assertEqual(
            PermohonanLembur.objects.get(tanggal=date(2026, 11, 4)).status,
            StatusPermohonanLembur.MENUNGGU_HRD,
        )

    def test_unknown_employee_writes_nothing(self):
        result = self._upload('9999999,2026-11-02\n1000001,2026-11-03\n')

        self.assertFalse(result.ok)
        self.assertIn('tidak ditemukan', result.errors[0].message)
        self.assertEqual(Dinas.objects.count(), 0)


class AdminDinasApiTests(TestCase):
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

    def _post(self, **overrides):
        payload = {
            'karyawan_id': self.employee.pk,
            'tanggal_mulai': '2026-11-02',
            'tanggal_selesai': '2026-11-04',
        }
        payload.update(overrides)
        return self.client.post('/api/admin/dinas/range/', payload, format='json')

    def test_creates_dinas_for_each_day_in_the_range(self):
        created = self._post()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['created'], 3)
        self.assertEqual(created.data['skipped'], 0)
        self.assertEqual(
            list(Dinas.objects.order_by('tanggal').values_list('tanggal', flat=True)),
            [date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4)],
        )
        self.assertEqual(PermohonanLembur.objects.count(), 0)

    def test_skips_days_that_already_have_dinas_or_approved_lembur(self):
        Dinas.objects.create(karyawan=self.employee, tanggal=date(2026, 11, 2))
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 3),
            status=StatusPermohonanLembur.APPROVED,
        )
        pending = PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 4),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )

        created = self._post()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['created'], 1)
        self.assertEqual(created.data['skipped'], 2)
        self.assertEqual(
            list(Dinas.objects.order_by('tanggal').values_list('tanggal', flat=True)),
            [date(2026, 11, 2), date(2026, 11, 4)],
        )
        pending.refresh_from_db()
        self.assertEqual(pending.status, StatusPermohonanLembur.MENUNGGU_HRD)
        self.assertTrue(
            PermohonanLembur.objects.filter(
                tanggal=date(2026, 11, 3),
                status=StatusPermohonanLembur.APPROVED,
            ).exists()
        )

        again = self._post()
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data['created'], 0)
        self.assertEqual(again.data['skipped'], 3)
        self.assertEqual(Dinas.objects.count(), 2)

    def test_rejects_reversed_range_too_long_range_and_bad_input(self):
        reversed_range = self._post(
            tanggal_mulai='2026-11-04', tanggal_selesai='2026-11-02'
        )
        self.assertEqual(reversed_range.status_code, 400)
        self.assertIn('tanggal_mulai', reversed_range.data['detail'])

        too_long = self._post(
            tanggal_mulai='2026-01-01', tanggal_selesai='2027-01-02'
        )
        self.assertEqual(too_long.status_code, 400)
        self.assertIn('366', too_long.data['detail'])

        unknown = self._post(karyawan_id='9999999')
        self.assertEqual(unknown.status_code, 400)
        self.assertIn('tidak ditemukan', unknown.data['karyawan_id'])

        bad_date = self._post(tanggal_selesai='04-11-2026')
        self.assertEqual(bad_date.status_code, 400)
        self.assertIn('yyyy-mm-dd', bad_date.data['tanggal_selesai'])
        self.assertEqual(Dinas.objects.count(), 0)

    def test_single_day_range_is_one_row(self):
        created = self._post(tanggal_mulai='2026-11-02', tanggal_selesai='2026-11-02')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['created'], 1)
        self.assertEqual(Dinas.objects.get().tanggal, date(2026, 11, 2))

    def test_accepts_the_maximum_range(self):
        start = date(2026, 1, 1)
        end = start + timedelta(days=365)
        created = self._post(
            tanggal_mulai=start.isoformat(),
            tanggal_selesai=end.isoformat(),
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['created'], 366)
        self.assertEqual(Dinas.objects.count(), 366)

    def test_list_filters_by_month_and_delete_removes_one_day(self):
        Dinas.objects.create(karyawan=self.employee, tanggal=date(2026, 11, 2))
        kept = Dinas.objects.create(karyawan=self.employee, tanggal=date(2026, 12, 1))

        listed = self.client.get(
            '/api/admin/dinas/',
            {'karyawan_id': self.employee.pk, 'bulan': '2026-11'},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]['tanggal'], '2026-11-02')
        self.assertEqual(listed.data[0]['karyawan_nama'], 'Budi')

        deleted = self.client.delete(f'/api/admin/dinas/{listed.data[0]["id"]}/')
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(list(Dinas.objects.values_list('pk', flat=True)), [kept.pk])

    def test_requires_admin(self):
        anonymous = APIClient().post(
            '/api/admin/dinas/range/',
            {
                'karyawan_id': self.employee.pk,
                'tanggal_mulai': '2026-11-02',
                'tanggal_selesai': '2026-11-02',
            },
            format='json',
        )
        self.assertEqual(anonymous.status_code, 401)

        self.employee.refresh_from_db()
        token = Token.objects.create(user=self.employee.user)
        employee_client = APIClient()
        employee_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        forbidden = employee_client.post(
            '/api/admin/dinas/range/',
            {
                'karyawan_id': self.employee.pk,
                'tanggal_mulai': '2026-11-02',
                'tanggal_selesai': '2026-11-02',
            },
            format='json',
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(Dinas.objects.count(), 0)
