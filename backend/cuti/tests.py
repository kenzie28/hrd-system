from datetime import date, timedelta

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from cuti.policy import can_request_cancellation, cancellation_cutoff
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

        self.today = date.today()
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
