from datetime import date, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from absensi.models import Absensi
from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from gaji.models import GajiTemp
from kalender_bersama.models import Langganan, NotifikasiDismiss
from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from lokasi.models import Lokasi
from shift.models import HariKerja, Shift
from state_manager.constants import STATE_MANAGER_PASSWORD
from state_manager.services import export_state_csv, import_state_csv


class StateManagerApiTests(TestCase):
    def setUp(self):
        self.lokasi = Lokasi.objects.create(id='99', nama='Headquarters')
        self.admin = Karyawan.objects.create(
            karyawan_id='0000003',
            nama='Kenzie Mihardja',
            lokasi_kerja=self.lokasi,
            jabatan='Director',
            wilayah='',
            level=8,
            must_change_password=False,
            cuti_tahunan=10,
        )
        self.admin.refresh_from_db()
        self.worker = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi Santoso',
            lokasi_kerja=self.lokasi,
            jabatan='Staff',
            wilayah='JKT',
            level=1,
            must_change_password=True,
            cuti_tahunan=12,
        )
        self.worker.refresh_from_db()
        self.admin_password_hash = self.admin.user.password
        self.token = Token.objects.create(user=self.admin.user)

        Shift.objects.create(
            lokasi_kerja=self.lokasi,
            hari=HariKerja.SENIN,
            jam_masuk=time(8, 0),
            jam_keluar=time(17, 0),
        )
        Liburan.objects.create(nama='Tahun Baru', tanggal=date(2026, 1, 1))
        Absensi.objects.create(
            karyawan=self.worker,
            lokasi=self.lokasi,
            tanggal=date(2026, 3, 2),
            jam_masuk=time(8, 5),
            durasi=timedelta(hours=8, minutes=55),
        )
        self.pending_cuti = PermohonanCuti.objects.create(
            karyawan=self.worker,
            tipe=TipeCuti.TAHUNAN,
            alasan='Liburan keluarga',
            tanggal_mulai=date(2026, 4, 1),
            tanggal_selesai=date(2026, 4, 3),
            status=StatusPermohonanCuti.MENUNGGU_SUPERVISOR,
            supervisor=self.admin,
        )
        self.approved_cuti = PermohonanCuti.objects.create(
            karyawan=self.worker,
            tipe=TipeCuti.SAKIT,
            alasan='Flu',
            tanggal_mulai=date(2026, 2, 10),
            tanggal_selesai=date(2026, 2, 10),
            status=StatusPermohonanCuti.APPROVED,
            supervisor=self.admin,
            hrd_approver=self.admin,
        )
        Cuti.objects.create(permohonan=self.approved_cuti, tanggal=date(2026, 2, 10))
        Langganan.objects.create(subscriber=self.admin, target=self.worker)
        NotifikasiDismiss.objects.create(
            subscriber=self.admin, permohonan=self.approved_cuti
        )
        PermohonanLembur.objects.create(
            karyawan=self.worker,
            alasan='Closing bulan',
            tanggal=date(2026, 3, 15),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
            supervisor=self.admin,
        )
        GajiTemp.objects.create(
            karyawan=self.worker,
            periode=date(2026, 2, 1),
            hadir='19/0/0',
            total_hadir=19,
            freq_lembur_6_jam=Decimal('0.68'),
            total_gaji=5_000_000,
        )
        self.superuser = User.objects.create_superuser(
            username='djangoadmin',
            password='secret',
            email='admin@example.com',
        )

        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_export_requires_password(self):
        response = self.client.get('/api/admin/state/export/')
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            '/api/admin/state/export/', {'password': 'wrong'}
        )
        self.assertEqual(response.status_code, 403)

    def test_export_includes_pending_cuti_and_lembur(self):
        response = self.client.get(
            '/api/admin/state/export/',
            {'password': STATE_MANAGER_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8')
        self.assertIn('#hrd-system-state,v1', body)
        self.assertIn('__table__,permohonan_cuti', body)
        self.assertIn('MENUNGGU_SUPERVISOR', body)
        self.assertIn('Liburan keluarga', body)
        self.assertIn('__table__,permohonan_lembur', body)
        self.assertIn('MENUNGGU_HRD', body)
        self.assertIn('Closing bulan', body)
        self.assertIn('__table__,cuti', body)
        self.assertIn('__table__,langganan', body)
        self.assertIn('__table__,notifikasi_dismiss', body)
        self.assertNotIn('djangoadmin', body)

    def test_round_trip_restore(self):
        csv_text = export_state_csv()
        original_cuti_count = PermohonanCuti.objects.count()
        original_lembur_count = PermohonanLembur.objects.count()
        original_hash = self.admin.user.password

        Lokasi.objects.create(id='XX', nama='Should vanish')
        self.worker.nama = 'CHANGED'
        self.worker.save(update_fields=['nama'])
        PermohonanCuti.objects.filter(pk=self.pending_cuti.pk).delete()
        self.assertTrue(Lokasi.objects.filter(id='XX').exists())
        self.assertEqual(Karyawan.objects.get(pk='1000001').nama, 'CHANGED')

        result = import_state_csv(csv_text)
        self.assertTrue(result.ok, result.errors)

        self.assertFalse(Lokasi.objects.filter(id='XX').exists())
        worker = Karyawan.objects.get(pk='1000001')
        self.assertEqual(worker.nama, 'Budi Santoso')
        self.assertEqual(worker.cuti_tahunan, 12)
        self.assertEqual(PermohonanCuti.objects.count(), original_cuti_count)
        self.assertEqual(PermohonanLembur.objects.count(), original_lembur_count)
        self.assertTrue(
            PermohonanCuti.objects.filter(
                alasan='Liburan keluarga',
                status=StatusPermohonanCuti.MENUNGGU_SUPERVISOR,
            ).exists()
        )
        self.assertTrue(
            PermohonanLembur.objects.filter(
                alasan='Closing bulan',
                status=StatusPermohonanLembur.MENUNGGU_HRD,
            ).exists()
        )
        self.assertTrue(
            Cuti.objects.filter(tanggal=date(2026, 2, 10)).exists()
        )
        self.assertTrue(
            Langganan.objects.filter(
                subscriber_id='0000003', target_id='1000001'
            ).exists()
        )
        self.assertTrue(
            NotifikasiDismiss.objects.filter(
                subscriber_id='0000003', permohonan=self.approved_cuti
            ).exists()
        )
        admin = Karyawan.objects.get(pk='0000003')
        self.assertEqual(admin.user.password, original_hash)
        self.assertTrue(User.objects.filter(username='djangoadmin').exists())
        gaji = GajiTemp.objects.get(karyawan_id='1000001', periode=date(2026, 2, 1))
        self.assertEqual(gaji.freq_lembur_6_jam, Decimal('0.68'))
        self.assertEqual(gaji.hadir, '19/0/0')

    def test_invalid_csv_writes_nothing(self):
        Karyawan.objects.filter(pk='1000001').update(nama='CHANGED')
        csv_text = export_state_csv()
        # Drop the gaji section so restore must reject the file.
        chopped = csv_text.split('__table__,gaji')[0]
        self.assertIn('CHANGED', chopped)

        result = import_state_csv(chopped)
        self.assertFalse(result.ok)
        self.assertTrue(
            any('gaji' in e.message for e in result.errors),
            result.errors,
        )
        self.assertEqual(Karyawan.objects.get(pk='1000001').nama, 'CHANGED')
        self.assertTrue(Lokasi.objects.filter(id='99').exists())

    def test_import_rejects_wrong_password_and_does_not_write(self):
        csv_text = export_state_csv()
        Karyawan.objects.filter(pk='1000001').update(nama='CHANGED')
        upload = BytesIO(csv_text.encode('utf-8'))
        upload.name = 'state.csv'

        response = self.client.post(
            '/api/admin/state/import/',
            {'file': upload, 'password': 'wrong'},
            format='multipart',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Karyawan.objects.get(pk='1000001').nama, 'CHANGED')

    def test_import_api_round_trip(self):
        csv_text = export_state_csv()
        Lokasi.objects.create(id='YY', nama='Temporary')
        upload = BytesIO(csv_text.encode('utf-8'))
        upload.name = 'state.csv'

        response = self.client.post(
            '/api/admin/state/import/',
            {'file': upload, 'password': STATE_MANAGER_PASSWORD},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertFalse(Lokasi.objects.filter(id='YY').exists())
        self.assertEqual(payload['counts']['karyawan'], 2)
        self.assertEqual(payload['counts']['permohonan_cuti'], 2)
        self.assertEqual(payload['counts']['permohonan_lembur'], 1)
        self.assertEqual(payload['counts']['langganan'], 1)
        self.assertEqual(payload['counts']['notifikasi_dismiss'], 1)

    def test_reset_requires_password_and_does_not_write(self):
        response = self.client.post(
            '/api/admin/state/reset/',
            {'password': 'wrong'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Karyawan.objects.count(), 2)
        self.assertTrue(PermohonanCuti.objects.exists())
        self.assertTrue(User.objects.filter(username='djangoadmin').exists())

    def test_reset_clears_state_and_preserves_seed_admin_login(self):
        response = self.client.post(
            '/api/admin/state/reset/',
            {'password': STATE_MANAGER_PASSWORD},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        admin = Karyawan.objects.get()
        self.assertEqual(admin.karyawan_id, '0000003')
        self.assertEqual(admin.nama, 'Kenzie Mihardja')
        self.assertIsNone(admin.lokasi_kerja_id)
        self.assertEqual(admin.user.password, self.admin_password_hash)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().pk, admin.user_id)
        self.assertTrue(Token.objects.filter(key=self.token.key).exists())

        self.assertFalse(Lokasi.objects.exists())
        self.assertFalse(Shift.objects.exists())
        self.assertFalse(Liburan.objects.exists())
        self.assertFalse(Absensi.objects.exists())
        self.assertFalse(PermohonanCuti.objects.exists())
        self.assertFalse(Cuti.objects.exists())
        self.assertFalse(PermohonanLembur.objects.exists())
        self.assertFalse(GajiTemp.objects.exists())
        self.assertFalse(Langganan.objects.exists())
        self.assertFalse(NotifikasiDismiss.objects.exists())
