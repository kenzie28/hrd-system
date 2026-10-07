from datetime import date, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from absensi.models import Absensi, Kehadiran, RekapAbsensi, StatusKehadiran
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

    def _clear(self, tables, password=STATE_MANAGER_PASSWORD):
        return self.client.post(
            '/api/admin/state/clear/',
            {'tables': tables, 'password': password},
            format='json',
            HTTP_X_STATE_MANAGER_PASSWORD=password,
        )

    def test_models_list_requires_password(self):
        response = self.client.get('/api/admin/state/models/')
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            '/api/admin/state/models/',
            HTTP_X_STATE_MANAGER_PASSWORD=STATE_MANAGER_PASSWORD,
        )
        self.assertEqual(response.status_code, 200, response.content)
        ids = [row['id'] for row in response.json()['models']]
        self.assertIn('absensi', ids)
        self.assertIn('gaji', ids)
        self.assertIn('kehadiran', ids)
        self.assertIn('rekap_absensi', ids)
        self.assertTrue(all(row['label'] for row in response.json()['models']))

    def test_clear_requires_password_and_does_not_write(self):
        response = self._clear(['liburan'], password='wrong')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Liburan.objects.exists())
        self.assertEqual(Karyawan.objects.count(), 2)

    def test_clear_rejects_unknown_or_empty_selection(self):
        unknown = self._clear(['bukan_model'])
        self.assertEqual(unknown.status_code, 400)
        self.assertIn('tidak dikenal', unknown.json()['detail'])
        self.assertTrue(Liburan.objects.exists())

        empty = self._clear([])
        self.assertEqual(empty.status_code, 400)
        self.assertTrue(GajiTemp.objects.exists())

    def test_clear_selected_models_only(self):
        punch = Absensi.objects.get()
        Kehadiran.objects.create(
            karyawan=self.worker,
            tanggal=punch.tanggal,
            absensi=punch,
            status=StatusKehadiran.HADIR,
        )
        Kehadiran.objects.create(
            karyawan=self.admin,
            tanggal=date(2026, 3, 3),
            status=StatusKehadiran.ALPA,
        )
        RekapAbsensi.objects.create(
            month=date(2026, 3, 1),
            karyawan=self.worker,
            hari_hadir=1,
        )

        response = self._clear(['absensi', 'liburan'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['deleted']['absensi'], 1)
        self.assertEqual(response.json()['deleted']['liburan'], 1)
        self.assertNotIn('gaji', response.json()['deleted'])

        self.assertFalse(Absensi.objects.exists())
        self.assertFalse(Liburan.objects.exists())
        self.assertFalse(Kehadiran.objects.filter(absensi__isnull=False).exists())
        self.assertTrue(
            Kehadiran.objects.filter(
                karyawan=self.admin, status=StatusKehadiran.ALPA
            ).exists()
        )
        self.assertTrue(RekapAbsensi.objects.exists())
        self.assertEqual(Karyawan.objects.count(), 2)
        self.assertTrue(Shift.objects.exists())
        self.assertTrue(GajiTemp.objects.exists())
        self.assertTrue(PermohonanCuti.objects.exists())
        self.assertTrue(Cuti.objects.exists())
        self.assertTrue(PermohonanLembur.objects.exists())
        self.assertTrue(Langganan.objects.exists())
        self.assertTrue(User.objects.filter(username='djangoadmin').exists())

    def test_clear_rekap_and_kehadiran_without_absensi(self):
        punch = Absensi.objects.get()
        Kehadiran.objects.create(
            karyawan=self.worker,
            tanggal=punch.tanggal,
            absensi=punch,
            status=StatusKehadiran.HADIR,
        )
        rekap = RekapAbsensi.objects.create(
            month=date(2026, 3, 1),
            karyawan=self.worker,
            hari_hadir=1,
        )
        rekap.catatan.create(tanggal=punch.tanggal, pesan='Telat')

        response = self._clear(['kehadiran', 'rekap_absensi'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Kehadiran.objects.exists())
        self.assertFalse(RekapAbsensi.objects.exists())
        self.assertTrue(Absensi.objects.filter(pk=punch.pk).exists())
        self.assertTrue(GajiTemp.objects.exists())

    def test_clear_karyawan_refuses_when_dependents_remain(self):
        response = self._clear(['karyawan'])
        self.assertEqual(response.status_code, 400, response.content)
        detail = response.json()['detail']
        self.assertIn('Gaji', detail)
        self.assertIn('Akun login', detail)
        self.assertIn('Permohonan cuti', detail)
        self.assertEqual(Karyawan.objects.count(), 2)
        self.assertTrue(GajiTemp.objects.exists())
        self.assertTrue(self.worker.user_id)

    def test_clear_karyawan_keeps_seed_admin_and_other_models(self):
        response = self._clear(
            [
                'karyawan',
                'auth_user',
                'absensi',
                'gaji',
                'langganan',
                'notifikasi_dismiss',
                'permohonan_cuti',
                'cuti',
                'permohonan_lembur',
            ]
        )
        self.assertEqual(response.status_code, 200, response.content)

        admin = Karyawan.objects.get()
        self.assertEqual(admin.karyawan_id, '0000003')
        self.assertEqual(admin.lokasi_kerja_id, '99')
        self.assertEqual(admin.user.password, self.admin_password_hash)
        self.assertTrue(Token.objects.filter(key=self.token.key).exists())
        self.assertTrue(User.objects.filter(username='djangoadmin').exists())
        self.assertEqual(User.objects.exclude(pk=admin.user_id).count(), 1)

        self.assertTrue(Lokasi.objects.filter(id='99').exists())
        self.assertTrue(Shift.objects.exists())
        self.assertTrue(Liburan.objects.exists())
        self.assertFalse(Absensi.objects.exists())
        self.assertFalse(GajiTemp.objects.exists())
        self.assertFalse(PermohonanCuti.objects.exists())
        self.assertFalse(Cuti.objects.exists())
        self.assertFalse(PermohonanLembur.objects.exists())
        self.assertFalse(Langganan.objects.exists())
        self.assertFalse(NotifikasiDismiss.objects.exists())

    def test_clear_lokasi_requires_shift_and_absensi(self):
        refused = self._clear(['lokasi'])
        self.assertEqual(refused.status_code, 400, refused.content)
        self.assertIn('Shift', refused.json()['detail'])
        self.assertIn('Absensi', refused.json()['detail'])
        self.assertTrue(Lokasi.objects.filter(id='99').exists())

        response = self._clear(['lokasi', 'shift', 'absensi'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Lokasi.objects.exists())
        self.assertFalse(Shift.objects.exists())
        self.assertFalse(Absensi.objects.exists())
        self.assertEqual(Karyawan.objects.count(), 2)
        self.assertIsNone(Karyawan.objects.get(pk='1000001').lokasi_kerja_id)
        self.assertTrue(GajiTemp.objects.exists())
        self.assertTrue(Liburan.objects.exists())

    def test_clear_permohonan_cuti_requires_days_and_dismissals(self):
        response = self._clear(['permohonan_cuti'])
        self.assertEqual(response.status_code, 400, response.content)
        detail = response.json()['detail']
        self.assertIn('Hari cuti', detail)
        self.assertIn('Notifikasi ditutup', detail)
        self.assertTrue(PermohonanCuti.objects.exists())
        self.assertTrue(Cuti.objects.exists())

    def test_clear_auth_user_unlinks_logins_except_admin(self):
        worker_user_id = self.worker.user_id
        response = self._clear(['auth_user'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['deleted']['auth_user'], 1)
        self.assertFalse(User.objects.filter(pk=worker_user_id).exists())
        self.worker.refresh_from_db()
        self.assertIsNone(self.worker.user_id)
        self.assertEqual(self.worker.nama, 'Budi Santoso')
        admin = Karyawan.objects.get(pk='0000003')
        self.assertEqual(admin.user.password, self.admin_password_hash)
        self.assertTrue(Token.objects.filter(key=self.token.key).exists())
        self.assertTrue(User.objects.filter(username='djangoadmin').exists())
        self.assertTrue(GajiTemp.objects.exists())
