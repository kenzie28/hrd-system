from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur, TipeLembur
from lembur.services import import_lembur_csv


class LemburCsvImportTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
        )

    def _upload(self, rows: str, header='karyawan_id,tanggal', tipe=TipeLembur.BIASA):
        upload = SimpleUploadedFile(
            'lembur.csv',
            f'{header}\n{rows}'.encode(),
            content_type='text/csv',
        )
        return import_lembur_csv(upload, tipe)

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
                and request.tipe == TipeLembur.BIASA
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

    def test_dinas_import_skips_a_day_that_already_has_approved_lembur(self):
        dinas = self._upload('1000001,2026-11-02\n', tipe=TipeLembur.DINAS)

        self.assertTrue(dinas.ok)
        self.assertEqual(dinas.created, 1)
        self.assertEqual(PermohonanLembur.objects.get().tipe, TipeLembur.DINAS)

        biasa = self._upload('1000001,2026-11-02\n')
        self.assertTrue(biasa.ok)
        self.assertEqual(biasa.created, 0)

        other = self._upload('1000001,2026-11-04\n')
        self.assertEqual(other.created, 1)
        self.assertEqual(
            PermohonanLembur.objects.get(tanggal=date(2026, 11, 4)).tipe,
            TipeLembur.BIASA,
        )
        blocked = self._upload('1000001,2026-11-04\n', tipe=TipeLembur.DINAS)
        self.assertEqual(blocked.created, 0)
        self.assertEqual(PermohonanLembur.objects.count(), 2)


class AdminLemburDayTests(TestCase):
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

    def _post(self, path, **overrides):
        payload = {
            'karyawan_id': self.employee.pk,
            'tanggal': '2026-11-02',
        }
        payload.update(overrides)
        return self.client.post(path, payload, format='json')

    def test_add_is_idempotent_and_remove_clears_approved(self):
        created = self._post('/api/admin/lembur/add/')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['status'], StatusPermohonanLembur.APPROVED)
        self.assertEqual(created.data['tanggal'], '2026-11-02')
        self.assertIsNone(created.data['supervisor'])
        self.assertEqual(PermohonanLembur.objects.count(), 1)

        again = self._post('/api/admin/lembur/add/')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data['id'], created.data['id'])
        self.assertEqual(PermohonanLembur.objects.count(), 1)

        removed = self._post('/api/admin/lembur/remove/')
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(PermohonanLembur.objects.count(), 0)

        removed_again = self._post('/api/admin/lembur/remove/')
        self.assertEqual(removed_again.status_code, 204)

    def test_remove_keeps_requests_that_are_not_approved(self):
        pending = PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        self._post('/api/admin/lembur/add/')

        removed = self._post('/api/admin/lembur/remove/')

        self.assertEqual(removed.status_code, 204)
        pending.refresh_from_db()
        self.assertEqual(pending.status, StatusPermohonanLembur.MENUNGGU_HRD)
        self.assertFalse(
            PermohonanLembur.objects.filter(
                status=StatusPermohonanLembur.APPROVED
            ).exists()
        )

    def test_rejects_unknown_employee_and_bad_date(self):
        unknown = self._post('/api/admin/lembur/add/', karyawan_id='9999999')
        self.assertEqual(unknown.status_code, 400)
        self.assertIn('tidak ditemukan', unknown.data['karyawan_id'])

        bad_date = self._post('/api/admin/lembur/add/', tanggal='02-11-2026')
        self.assertEqual(bad_date.status_code, 400)
        self.assertIn('yyyy-mm-dd', bad_date.data['tanggal'])
        self.assertEqual(PermohonanLembur.objects.count(), 0)

    def test_requires_admin(self):
        anonymous = APIClient().post(
            '/api/admin/lembur/add/',
            {'karyawan_id': self.employee.pk, 'tanggal': '2026-11-02'},
            format='json',
        )
        self.assertEqual(anonymous.status_code, 401)

        self.employee.refresh_from_db()
        token = Token.objects.create(user=self.employee.user)
        employee_client = APIClient()
        employee_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        forbidden = employee_client.post(
            '/api/admin/lembur/add/',
            {'karyawan_id': self.employee.pk, 'tanggal': '2026-11-02'},
            format='json',
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(PermohonanLembur.objects.count(), 0)

    def test_hrd_approve_rejected_when_day_already_approved(self):
        pending = PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusPermohonanLembur.APPROVED,
            tipe=TipeLembur.DINAS,
        )

        response = self.client.post(f'/api/admin/lembur/{pending.pk}/approve/')

        self.assertEqual(response.status_code, 400)
        self.assertIn('approved', response.data['detail'])
        pending.refresh_from_db()
        self.assertEqual(pending.status, StatusPermohonanLembur.MENUNGGU_HRD)
        self.assertEqual(
            PermohonanLembur.objects.filter(
                status=StatusPermohonanLembur.APPROVED
            ).count(),
            1,
        )
