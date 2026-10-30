from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from cuti.policy import (
    can_request_cancellation,
    cancellation_cutoff,
    tahunan_range_errors,
)
from cuti.services import import_cuti_csv
from karyawan.models import Karyawan
from lokasi.models import Lokasi


def _token_client(karyawan: Karyawan) -> APIClient:
    client = APIClient()
    token = Token.objects.create(user=karyawan.user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


class CancellationCutoffTests(TestCase):
    def test_september_cutoff_is_august_first(self):
        self.assertEqual(cancellation_cutoff(date(2026, 9, 8)), date(2026, 8, 1))

    def test_january_cutoff_is_december_first(self):
        self.assertEqual(cancellation_cutoff(date(2026, 1, 15)), date(2025, 12, 1))


class TahunanRangePolicyTests(TestCase):
    def test_six_days_rejected(self):
        today = date(2026, 9, 8)
        start = today + timedelta(days=28)
        errors = tahunan_range_errors(start, start + timedelta(days=5), today=today)
        self.assertIn('tanggal_selesai', errors)

    def test_five_days_ok_with_28_days_notice(self):
        today = date(2026, 9, 8)
        start = today + timedelta(days=28)
        errors = tahunan_range_errors(start, start + timedelta(days=4), today=today)
        self.assertEqual(errors, {})

    def test_four_days_rejected_without_28_days_notice(self):
        today = date(2026, 9, 8)
        start = today + timedelta(days=27)
        errors = tahunan_range_errors(start, start + timedelta(days=3), today=today)
        self.assertIn('tanggal_mulai', errors)

    def test_three_days_needs_no_advance_notice(self):
        today = date(2026, 9, 8)
        start = today + timedelta(days=1)
        errors = tahunan_range_errors(start, start + timedelta(days=2), today=today)
        self.assertEqual(errors, {})

    def test_four_days_ok_on_exactly_28th_day(self):
        today = date(2026, 9, 8)
        start = today + timedelta(days=28)
        errors = tahunan_range_errors(start, start + timedelta(days=3), today=today)
        self.assertEqual(errors, {})


class CutiCsvImportTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
            cuti_tahunan=2,
        )

    def _upload(self, rows: str, tipe: str):
        upload = SimpleUploadedFile(
            'cuti.csv',
            f'karyawan_id,tanggal\n{rows}'.encode(),
            content_type='text/csv',
        )
        return import_cuti_csv(upload, tipe)

    def test_tahunan_creates_approved_requests_and_deducts_quota(self):
        result = self._upload(
            '1000001,2026-11-02\n1000001,2026-11-03\n',
            TipeCuti.TAHUNAN,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.created, 2)
        requests = PermohonanCuti.objects.order_by('tanggal_mulai')
        self.assertEqual(requests.count(), 2)
        self.assertTrue(
            all(
                request.status == StatusPermohonanCuti.APPROVED
                and request.supervisor is None
                and request.hrd_approver is None
                for request in requests
            )
        )
        self.assertEqual(Cuti.objects.count(), 2)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.cuti_tahunan, 0)

    def test_sakit_does_not_deduct_quota_and_duplicate_is_skipped(self):
        first = self._upload(
            '1000001;2026-11-02\n1000001;2026-11-02\n'.replace(';', ','),
            TipeCuti.SAKIT,
        )
        second = self._upload('1000001,2026-11-02\n', TipeCuti.SAKIT)

        self.assertTrue(first.ok)
        self.assertEqual(first.created, 1)
        self.assertTrue(second.ok)
        self.assertEqual(second.created, 0)
        self.assertEqual(PermohonanCuti.objects.get().tipe, TipeCuti.SAKIT)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.cuti_tahunan, 2)

    def test_insufficient_tahunan_quota_writes_nothing(self):
        result = self._upload(
            '1000001,2026-11-02\n'
            '1000001,2026-11-03\n'
            '1000001,2026-11-04\n',
            TipeCuti.TAHUNAN,
        )

        self.assertFalse(result.ok)
        self.assertIn('tidak cukup', result.errors[0].message)
        self.assertEqual(PermohonanCuti.objects.count(), 0)
        self.assertEqual(Cuti.objects.count(), 0)


class PortalCutiCancellationTests(TestCase):
    def setUp(self):
        self.lokasi = Lokasi.objects.create(id='99', nama='Headquarters')
        self.hrd = Karyawan.objects.create(
            karyawan_id='0000003',
            nama='Kenzie Mihardja',
            lokasi_kerja=self.lokasi,
            jabatan='Director',
            level=8,
            cuti_tahunan=12,
        )
        self.supervisor = Karyawan.objects.create(
            karyawan_id='1000005',
            nama='Supervisor Lima',
            lokasi_kerja=self.lokasi,
            jabatan='Supervisor',
            level=5,
            cuti_tahunan=12,
        )
        self.worker = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi Santoso',
            lokasi_kerja=self.lokasi,
            jabatan='Staff',
            level=1,
            cuti_tahunan=12,
        )
        self.hrd.refresh_from_db()
        self.supervisor.refresh_from_db()
        self.worker.refresh_from_db()

        self.worker_client = _token_client(self.worker)
        self.supervisor_client = _token_client(self.supervisor)
        self.hrd_client = _token_client(self.hrd)

        self.today = timezone.localdate()
        self.start = self.today + timedelta(days=7)
        self.end = self.start + timedelta(days=1)

    def _create_pending(self):
        response = self.worker_client.post(
            '/api/portal/cuti/',
            {
                'tipe': TipeCuti.TAHUNAN,
                'alasan': 'Liburan',
                'tanggal_mulai': self.start.isoformat(),
                'tanggal_selesai': self.end.isoformat(),
                'supervisor': self.supervisor.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['id']

    def _approve_original(self, pk):
        response = self.supervisor_client.post(f'/api/portal/cuti/{pk}/approve/')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.hrd_client.post(f'/api/admin/cuti/{pk}/approve/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], StatusPermohonanCuti.APPROVED)
        return response.data

    def test_instant_cancel_before_hrd_does_not_touch_quota(self):
        pk = self._create_pending()
        response = self.worker_client.post(f'/api/portal/cuti/{pk}/cancel/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], StatusPermohonanCuti.DIBATALKAN)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.cuti_tahunan, 12)

    def test_batal_after_hrd_restores_cuti_tahunan(self):
        pk = self._create_pending()
        self._approve_original(pk)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.cuti_tahunan, 10)
        self.assertEqual(Cuti.objects.filter(permohonan_id=pk).count(), 2)

        response = self.worker_client.post(f'/api/portal/cuti/{pk}/cancel/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data['status'],
            StatusPermohonanCuti.MENUNGGU_PEMBATALAN_SUPERVISOR,
        )
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.cuti_tahunan, 10)

        approvals = self.supervisor_client.get('/api/portal/cuti/approvals/')
        self.assertEqual(approvals.status_code, 200)
        self.assertTrue(any(item['id'] == pk for item in approvals.data))

        response = self.supervisor_client.post(f'/api/portal/cuti/{pk}/approve/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data['status'],
            StatusPermohonanCuti.MENUNGGU_PEMBATALAN_HRD,
        )

        queue = self.hrd_client.get('/api/admin/cuti/')
        self.assertEqual(queue.status_code, 200)
        self.assertTrue(any(item['id'] == pk for item in queue.data))

        response = self.hrd_client.post(f'/api/admin/cuti/{pk}/approve/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], StatusPermohonanCuti.DIBATALKAN)
        self.assertEqual(response.data['hari_dihapus'], 2)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.cuti_tahunan, 12)
        self.assertEqual(Cuti.objects.filter(permohonan_id=pk).count(), 0)

    def test_supervisor_reject_pembatalan_keeps_approved_and_quota(self):
        pk = self._create_pending()
        self._approve_original(pk)
        self.worker_client.post(f'/api/portal/cuti/{pk}/cancel/')
        response = self.supervisor_client.post(f'/api/portal/cuti/{pk}/reject/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], StatusPermohonanCuti.APPROVED)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.cuti_tahunan, 10)
        self.assertEqual(Cuti.objects.filter(permohonan_id=pk).count(), 2)

    def test_hrd_reject_pembatalan_keeps_approved_and_quota(self):
        pk = self._create_pending()
        self._approve_original(pk)
        self.worker_client.post(f'/api/portal/cuti/{pk}/cancel/')
        self.supervisor_client.post(f'/api/portal/cuti/{pk}/approve/')
        response = self.hrd_client.post(f'/api/admin/cuti/{pk}/reject/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], StatusPermohonanCuti.APPROVED)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.cuti_tahunan, 10)
        self.assertEqual(Cuti.objects.filter(permohonan_id=pk).count(), 2)

    def test_cannot_batal_after_cutoff_month(self):
        cutoff = cancellation_cutoff(self.today)
        too_old = cutoff - timedelta(days=1)
        permohonan = PermohonanCuti.objects.create(
            karyawan=self.worker,
            tipe=TipeCuti.TAHUNAN,
            alasan='Lama',
            tanggal_mulai=too_old,
            tanggal_selesai=too_old,
            status=StatusPermohonanCuti.APPROVED,
            supervisor=self.supervisor,
            hrd_approver=self.hrd,
        )
        Cuti.objects.create(permohonan=permohonan, tanggal=too_old)
        self.assertFalse(can_request_cancellation(permohonan, today=self.today))

        listed = self.worker_client.get('/api/portal/cuti/')
        row = next(item for item in listed.data if item['id'] == permohonan.pk)
        self.assertFalse(row['can_batal'])

        response = self.worker_client.post(
            f'/api/portal/cuti/{permohonan.pk}/cancel/'
        )
        self.assertEqual(response.status_code, 400)

    def test_can_batal_from_previous_calendar_month(self):
        cutoff = cancellation_cutoff(self.today)
        permohonan = PermohonanCuti.objects.create(
            karyawan=self.worker,
            tipe=TipeCuti.TAHUNAN,
            alasan='Bulan lalu',
            tanggal_mulai=cutoff,
            tanggal_selesai=cutoff,
            status=StatusPermohonanCuti.APPROVED,
            supervisor=self.supervisor,
            hrd_approver=self.hrd,
        )
        self.assertTrue(can_request_cancellation(permohonan, today=self.today))
        listed = self.worker_client.get('/api/portal/cuti/')
        row = next(item for item in listed.data if item['id'] == permohonan.pk)
        self.assertTrue(row['can_batal'])


class PortalCutiTahunanRulesTests(TestCase):
    def setUp(self):
        self.lokasi = Lokasi.objects.create(id='99', nama='Headquarters')
        self.supervisor = Karyawan.objects.create(
            karyawan_id='1000005',
            nama='Supervisor Lima',
            lokasi_kerja=self.lokasi,
            jabatan='Supervisor',
            level=5,
            cuti_tahunan=12,
        )
        self.worker = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi Santoso',
            lokasi_kerja=self.lokasi,
            jabatan='Staff',
            level=1,
            cuti_tahunan=12,
        )
        self.worker.refresh_from_db()
        self.client = _token_client(self.worker)
        self.today = timezone.localdate()

    def _post(self, tipe, start, end):
        return self.client.post(
            '/api/portal/cuti/',
            {
                'tipe': tipe,
                'alasan': 'Liburan',
                'tanggal_mulai': start.isoformat(),
                'tanggal_selesai': end.isoformat(),
                'supervisor': self.supervisor.pk,
            },
            format='json',
        )

    def test_rejects_more_than_five_consecutive_days(self):
        start = self.today + timedelta(days=28)
        response = self._post(TipeCuti.TAHUNAN, start, start + timedelta(days=5))
        self.assertEqual(response.status_code, 400)
        self.assertIn('tanggal_selesai', response.data)

    def test_rejects_four_days_without_28_days_notice(self):
        start = self.today + timedelta(days=27)
        response = self._post(TipeCuti.TAHUNAN, start, start + timedelta(days=3))
        self.assertEqual(response.status_code, 400)
        self.assertIn('tanggal_mulai', response.data)

    def test_accepts_five_days_with_28_days_notice(self):
        start = self.today + timedelta(days=28)
        response = self._post(TipeCuti.TAHUNAN, start, start + timedelta(days=4))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['jumlah_hari'], 5)

    def test_accepts_three_days_without_advance_notice(self):
        start = self.today + timedelta(days=1)
        response = self._post(TipeCuti.TAHUNAN, start, start + timedelta(days=2))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['jumlah_hari'], 3)

    def test_other_types_are_not_limited_to_five_days(self):
        start = self.today + timedelta(days=1)
        response = self._post(TipeCuti.IZIN_OFF, start, start + timedelta(days=5))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['jumlah_hari'], 6)


class CutiLedgerTests(TestCase):
    def test_tahunan_rows_include_remaining_quota(self):
        employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=1,
            cuti_tahunan=7,
        )
        tahunan = PermohonanCuti.objects.create(
            karyawan=employee,
            tipe=TipeCuti.TAHUNAN,
            tanggal_mulai=date(2026, 11, 2),
            tanggal_selesai=date(2026, 11, 2),
            status=StatusPermohonanCuti.APPROVED,
        )
        sakit = PermohonanCuti.objects.create(
            karyawan=employee,
            tipe=TipeCuti.SAKIT,
            tanggal_mulai=date(2026, 11, 3),
            tanggal_selesai=date(2026, 11, 3),
            status=StatusPermohonanCuti.APPROVED,
        )
        Cuti.objects.create(permohonan=tahunan, tanggal=date(2026, 11, 2))
        Cuti.objects.create(permohonan=sakit, tanggal=date(2026, 11, 3))

        response = APIClient().get('/api/cuti/')
        self.assertEqual(response.status_code, 200)
        by_tipe = {row['tipe']: row for row in response.data}
        self.assertEqual(by_tipe[TipeCuti.TAHUNAN]['sisa_cuti_tahunan'], 7)
        self.assertIsNone(by_tipe[TipeCuti.SAKIT]['sisa_cuti_tahunan'])
