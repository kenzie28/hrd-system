from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from kalender_bersama.models import Langganan, NotifikasiDismiss
from karyawan.models import Karyawan
from lokasi.models import Lokasi


def _token_client(karyawan: Karyawan) -> APIClient:
    client = APIClient()
    token = Token.objects.create(user=karyawan.user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


class KalenderBersamaPortalTests(TestCase):
    def setUp(self):
        self.lokasi = Lokasi.objects.create(id='99', nama='Headquarters')
        self.alice = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Alice Sari',
            lokasi_kerja=self.lokasi,
            jabatan='Staff',
            level=1,
            cuti_tahunan=12,
        )
        self.bob = Karyawan.objects.create(
            karyawan_id='1000002',
            nama='Budi Santoso',
            lokasi_kerja=self.lokasi,
            jabatan='Staff',
            level=1,
            cuti_tahunan=12,
        )
        self.citra = Karyawan.objects.create(
            karyawan_id='1000003',
            nama='Citra Lestari',
            lokasi_kerja=self.lokasi,
            jabatan='Supervisor',
            level=5,
            cuti_tahunan=12,
        )
        self.alice.refresh_from_db()
        self.bob.refresh_from_db()
        self.citra.refresh_from_db()
        self.alice_client = _token_client(self.alice)
        self.bob_client = _token_client(self.bob)
        self.today = timezone.localdate()

    def _approved_cuti(self, karyawan, start, end, tipe=TipeCuti.TAHUNAN):
        permohonan = PermohonanCuti.objects.create(
            karyawan=karyawan,
            tipe=tipe,
            alasan='Libur',
            tanggal_mulai=start,
            tanggal_selesai=end,
            status=StatusPermohonanCuti.APPROVED,
            supervisor=self.citra,
            hrd_approver=self.citra,
        )
        day = start
        while day <= end:
            Cuti.objects.create(permohonan=permohonan, tanggal=day)
            day += timedelta(days=1)
        return permohonan

    def test_subscribe_and_unsubscribe(self):
        response = self.alice_client.post(
            '/api/portal/kalender-bersama/langganan/',
            {'karyawan_id': self.bob.karyawan_id},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['karyawan_id'], self.bob.karyawan_id)
        self.assertEqual(response.data['nama'], self.bob.nama)

        listed = self.alice_client.get('/api/portal/kalender-bersama/langganan/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]['karyawan_id'], self.bob.karyawan_id)

        deleted = self.alice_client.delete(
            f'/api/portal/kalender-bersama/langganan/{self.bob.karyawan_id}/'
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(Langganan.objects.filter(subscriber=self.alice).count(), 0)

    def test_cannot_subscribe_to_self(self):
        response = self.alice_client.post(
            '/api/portal/kalender-bersama/langganan/',
            {'karyawan_id': self.alice.karyawan_id},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('diri sendiri', response.data['detail'])

    def test_duplicate_subscribe_rejected(self):
        Langganan.objects.create(subscriber=self.alice, target=self.bob)
        response = self.alice_client.post(
            '/api/portal/kalender-bersama/langganan/',
            {'karyawan_id': self.bob.karyawan_id},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('sudah ada', response.data['detail'])

    def test_subscribe_unknown_karyawan(self):
        response = self.alice_client.post(
            '/api/portal/kalender-bersama/langganan/',
            {'karyawan_id': '9999999'},
            format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_unsubscribe_missing_returns_404(self):
        response = self.alice_client.delete(
            f'/api/portal/kalender-bersama/langganan/{self.bob.karyawan_id}/'
        )
        self.assertEqual(response.status_code, 404)

    def test_search_requires_two_chars_and_excludes_self(self):
        empty = self.alice_client.get('/api/portal/kalender-bersama/karyawan/?q=A')
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.data, [])

        by_name = self.alice_client.get('/api/portal/kalender-bersama/karyawan/?q=Budi')
        self.assertEqual(by_name.status_code, 200)
        ids = [row['karyawan_id'] for row in by_name.data]
        self.assertIn(self.bob.karyawan_id, ids)
        self.assertNotIn(self.alice.karyawan_id, ids)

        by_id = self.alice_client.get(
            f'/api/portal/kalender-bersama/karyawan/?q={self.citra.karyawan_id}'
        )
        self.assertEqual(len(by_id.data), 1)
        self.assertEqual(by_id.data[0]['karyawan_id'], self.citra.karyawan_id)
        self.assertFalse(by_id.data[0]['sudah_di_grup'])

        Langganan.objects.create(subscriber=self.alice, target=self.citra)
        marked = self.alice_client.get(
            f'/api/portal/kalender-bersama/karyawan/?q={self.citra.karyawan_id}'
        )
        self.assertTrue(marked.data[0]['sudah_di_grup'])

    def test_search_does_not_dump_full_roster(self):
        response = self.alice_client.get('/api/portal/kalender-bersama/karyawan/')
        self.assertEqual(response.data, [])

    def test_calendar_only_shows_subscribed_approved_leave(self):
        start = self.today + timedelta(days=2)
        end = start + timedelta(days=1)
        self._approved_cuti(self.bob, start, end)
        self._approved_cuti(self.citra, start, end, tipe=TipeCuti.SAKIT)
        pending = PermohonanCuti.objects.create(
            karyawan=self.bob,
            tipe=TipeCuti.IZIN_OFF,
            alasan='Pending',
            tanggal_mulai=start,
            tanggal_selesai=start,
            status=StatusPermohonanCuti.MENUNGGU_HRD,
            supervisor=self.citra,
        )
        Cuti.objects.create(permohonan=pending, tanggal=start)

        Langganan.objects.create(subscriber=self.alice, target=self.bob)
        dari = self.today.replace(day=1)
        if dari.month == 12:
            sampai = dari.replace(year=dari.year + 1, month=2, day=1) - timedelta(days=1)
        elif dari.month == 11:
            sampai = dari.replace(year=dari.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            sampai = dari.replace(month=dari.month + 2, day=1) - timedelta(days=1)

        response = self.alice_client.get(
            '/api/portal/kalender-bersama/kalender/',
            {'dari': dari.isoformat(), 'sampai': sampai.isoformat()},
        )
        self.assertEqual(response.status_code, 200, response.data)
        ids = {row['karyawan_id'] for row in response.data}
        self.assertEqual(ids, {self.bob.karyawan_id})
        types = {row['tipe'] for row in response.data}
        self.assertEqual(types, {TipeCuti.TAHUNAN})

        missing_range = self.alice_client.get('/api/portal/kalender-bersama/kalender/')
        self.assertEqual(missing_range.status_code, 400)

    def test_notifications_within_14_days_and_dismiss(self):
        soon = self.today + timedelta(days=5)
        later = self.today + timedelta(days=20)
        soon_cuti = self._approved_cuti(self.bob, soon, soon)
        self._approved_cuti(self.bob, later, later)
        self._approved_cuti(self.citra, soon, soon)

        Langganan.objects.create(subscriber=self.alice, target=self.bob)
        response = self.alice_client.get('/api/portal/kalender-bersama/notifikasi/')
        self.assertEqual(response.status_code, 200)
        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [soon_cuti.id])

        dismissed = self.alice_client.post(
            f'/api/portal/kalender-bersama/notifikasi/{soon_cuti.id}/dismiss/'
        )
        self.assertEqual(dismissed.status_code, 200, dismissed.data)
        self.assertTrue(
            NotifikasiDismiss.objects.filter(
                subscriber=self.alice, permohonan=soon_cuti
            ).exists()
        )
        after = self.alice_client.get('/api/portal/kalender-bersama/notifikasi/')
        self.assertEqual(after.data, [])

    def test_cannot_dismiss_other_employees_notification(self):
        soon = self.today + timedelta(days=3)
        permohonan = self._approved_cuti(self.bob, soon, soon)
        Langganan.objects.create(subscriber=self.alice, target=self.bob)
        response = self.bob_client.post(
            f'/api/portal/kalender-bersama/notifikasi/{permohonan.id}/dismiss/'
        )
        self.assertEqual(response.status_code, 404)

    def test_cancellation_pending_still_visible(self):
        start = self.today + timedelta(days=1)
        permohonan = self._approved_cuti(self.bob, start, start)
        permohonan.status = StatusPermohonanCuti.MENUNGGU_PEMBATALAN_SUPERVISOR
        permohonan.save(update_fields=['status'])
        Langganan.objects.create(subscriber=self.alice, target=self.bob)

        notif = self.alice_client.get('/api/portal/kalender-bersama/notifikasi/')
        self.assertEqual([row['id'] for row in notif.data], [permohonan.id])

        cal = self.alice_client.get(
            '/api/portal/kalender-bersama/kalender/',
            {'dari': start.isoformat(), 'sampai': start.isoformat()},
        )
        self.assertEqual(len(cal.data), 1)
