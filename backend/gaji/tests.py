import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from absensi.models import Kehadiran, StatusKehadiran
from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from gaji.jobs import run_proses_gaji
from gaji.models import Gaji, ProsesGajiJob, StatusProsesGaji
from gaji.services import write_gaji
from gaji.ter import ter_fraction
from karyawan.models import Karyawan, StatusKTk
from koreksi.models import Koreksi, TipeKoreksi
from lembur.models import PermohonanLembur, StatusPermohonanLembur, TipeLembur
from obat.models import TunjanganObat


def _cuti(karyawan, tipe, *days):
    permohonan = PermohonanCuti.objects.create(
        karyawan=karyawan,
        tipe=tipe,
        tanggal_mulai=min(days),
        tanggal_selesai=max(days),
        status=StatusPermohonanCuti.APPROVED,
    )
    for day in days:
        Cuti.objects.create(permohonan=permohonan, tanggal=day)
    return permohonan


class TerFractionTests(TestCase):
    def test_shared_boundary_stays_in_the_lower_bracket(self):
        self.assertEqual(ter_fraction('A', 5_400_000), Decimal('0'))
        self.assertEqual(ter_fraction('A', 5_400_001), Decimal('0.0025'))
        self.assertEqual(ter_fraction('B', 6_200_000), Decimal('0'))
        self.assertEqual(ter_fraction('B', 6_200_001), Decimal('0.0025'))
        self.assertEqual(ter_fraction('C', 6_600_000), Decimal('0'))
        self.assertEqual(ter_fraction('C', 6_600_001), Decimal('0.0025'))

    def test_open_top_bracket(self):
        self.assertEqual(ter_fraction('A', 1_400_000_000), Decimal('0.33'))
        self.assertEqual(ter_fraction('A', 1_400_000_001), Decimal('0.34'))
        self.assertEqual(ter_fraction('B', 1_405_000_000), Decimal('0.33'))
        self.assertEqual(ter_fraction('B', 1_405_000_001), Decimal('0.34'))
        self.assertEqual(ter_fraction('C', 1_419_000_000), Decimal('0.33'))
        self.assertEqual(ter_fraction('C', 1_419_000_001), Decimal('0.34'))

    def test_blank_unknown_and_non_positive_income_are_zero(self):
        self.assertEqual(ter_fraction('', 10_000_000), Decimal('0'))
        self.assertEqual(ter_fraction('Z', 10_000_000), Decimal('0'))
        self.assertEqual(ter_fraction('A', 0), Decimal('0'))
        self.assertEqual(ter_fraction('A', -1), Decimal('0'))


class ProsesGajiCalculationTests(TestCase):
    def setUp(self):
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=3,
            jabatan='Staff',
            base_gaji=4_500_000,
            gaji_bulanan=6_000_000,
            lembur_dibayar=True,
            status_k_tk=StatusKTk.TK,
        )
        self.periode = date(2026, 11, 1)

    def test_snapshots_attendance_sums_bpjs_and_pph(self):
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusKehadiran.HADIR,
            menit_telat=10,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 3),
            status=StatusKehadiran.HADIR,
            lembur=90,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 4),
            status=StatusKehadiran.HADIR,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 5),
            status=StatusKehadiran.ALPA,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 6),
            status=StatusKehadiran.ALPA,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 10, 31),
            status=StatusKehadiran.ALPA,
        )

        _cuti(self.employee, TipeCuti.SAKIT, date(2026, 11, 9), date(2026, 11, 9))
        _cuti(self.employee, TipeCuti.SAKIT, date(2026, 11, 10))
        _cuti(self.employee, TipeCuti.TAHUNAN, date(2026, 11, 11))
        _cuti(self.employee, TipeCuti.MENIKAH, date(2026, 11, 12))
        _cuti(self.employee, TipeCuti.DUKA_CITA, date(2026, 11, 13))
        _cuti(self.employee, TipeCuti.IZIN_OFF, date(2026, 11, 16))
        _cuti(self.employee, TipeCuti.IZIN_TELAT, date(2026, 11, 17))

        for day in (date(2026, 11, 18), date(2026, 11, 18), date(2026, 11, 19)):
            PermohonanLembur.objects.create(
                karyawan=self.employee,
                tanggal=day,
                tipe=TipeLembur.DINAS,
                status=StatusPermohonanLembur.APPROVED,
            )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 20),
            tipe=TipeLembur.DINAS,
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 21),
            tipe=TipeLembur.BIASA,
            status=StatusPermohonanLembur.APPROVED,
        )

        TunjanganObat.objects.create(
            karyawan=self.employee, nominal=100_000, bulan=self.periode
        )
        TunjanganObat.objects.create(
            karyawan=self.employee, nominal=50_000, bulan=self.periode
        )
        TunjanganObat.objects.create(
            karyawan=self.employee, nominal=999, bulan=date(2026, 10, 1)
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ABSENSI,
            nominal=20_000,
            bulan=self.periode,
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ABSENSI,
            nominal=-5_000,
            bulan=self.periode,
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ADMIN,
            nominal=-10_000,
            bulan=self.periode,
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ADMIN,
            nominal=-3_000,
            bulan=self.periode,
        )

        gaji = write_gaji(self.employee, date(2026, 11, 15))

        self.assertEqual(gaji.periode, self.periode)
        self.assertEqual(gaji.level, 3)
        self.assertEqual(gaji.jabatan, 'Staff')
        self.assertTrue(gaji.lembur_dibayar)
        self.assertEqual(gaji.status_k_tk, StatusKTk.TK)
        self.assertEqual(gaji.ter_status, 'A')
        self.assertEqual(gaji.base_gaji_bpjs, 4_500_000)
        self.assertEqual(gaji.gaji_bulanan, 6_000_000)
        self.assertEqual(gaji.hari_hadir, 3)
        self.assertEqual(gaji.hari_telat, 1)
        self.assertEqual(gaji.total_menit_telat, 10)
        self.assertEqual(gaji.hari_alpa, 2)
        self.assertEqual(gaji.hari_lembur, 1)
        self.assertEqual(gaji.jam_lembur, 2)
        self.assertEqual(gaji.hari_sakit, 2)
        self.assertEqual(gaji.hari_cuti, 1)
        self.assertEqual(gaji.hari_cuti_tambahan, 2)
        self.assertEqual(gaji.hari_off, 1)
        self.assertEqual(gaji.hari_dinas, 2)
        self.assertEqual(gaji.tunjangan_obat, 150_000)
        self.assertEqual(gaji.koreksi_absensi, 15_000)
        self.assertEqual(gaji.koreksi_admin, -13_000)
        self.assertEqual(gaji.pot_bpjs_jht, 90_000)
        self.assertEqual(gaji.pot_bpjs_jp, 45_000)
        self.assertEqual(gaji.pot_bpjs_kesehatan, 45_000)
        self.assertEqual(gaji.beban_bpjs_kesehatan, 180_000)
        self.assertEqual(gaji.beban_bpjs_jht, 166_500)
        self.assertEqual(gaji.beban_bpjs_jp, 90_000)
        self.assertEqual(gaji.beban_bpjs_jkm, 13_500)
        self.assertEqual(gaji.beban_bjps_jkk, 10_800)
        self.assertEqual(gaji.total_bpjs_benefit, 204_300)
        self.assertEqual(gaji.pot_alpa, 600_000)
        self.assertEqual(gaji.gaji_lembur, 0)
        self.assertEqual(gaji.tunjangan_dinas, 0)
        self.assertEqual(gaji.uang_terima_kasih, 0)
        self.assertEqual(gaji.net_penghasilan, 5_756_300)
        self.assertEqual(gaji.persentase_pph21, Decimal('0.50'))
        self.assertEqual(gaji.pot_pph21, 28_782)
        self.assertEqual(gaji.total_gaji, 5_523_218)
        self.assertEqual(
            gaji.total_gaji,
            gaji.net_penghasilan - gaji.total_bpjs_benefit - gaji.pot_pph21,
        )

    def test_rerun_updates_the_same_row(self):
        first = write_gaji(self.employee, self.periode)
        first.gaji_lembur = 999
        first.save(update_fields=['gaji_lembur'])
        self.employee.base_gaji = 8_000_000
        self.employee.gaji_bulanan = 7_000_000
        self.employee.lembur_dibayar = False
        self.employee.jabatan = 'Senior'
        self.employee.status_k_tk = StatusKTk.K3
        self.employee.save()

        again = write_gaji(self.employee, self.periode)

        self.assertEqual(again.pk, first.pk)
        self.assertEqual(Gaji.objects.count(), 1)
        self.assertEqual(again.base_gaji_bpjs, 8_000_000)
        self.assertEqual(again.gaji_bulanan, 7_000_000)
        self.assertFalse(again.lembur_dibayar)
        self.assertEqual(again.jabatan, 'Senior')
        self.assertEqual(again.status_k_tk, StatusKTk.K3)
        self.assertEqual(again.ter_status, 'C')
        self.assertEqual(again.gaji_lembur, 0)
        self.assertEqual(again.pot_bpjs_jht, 160_000)

    def test_half_up_rounding_for_alpa_and_bpjs(self):
        self.employee.base_gaji = 100
        self.employee.gaji_bulanan = 10
        self.employee.status_k_tk = ''
        self.employee.save()
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusKehadiran.ALPA,
        )

        gaji = write_gaji(self.employee, self.periode)

        self.assertEqual(gaji.hari_alpa, 1)
        self.assertEqual(gaji.pot_alpa, 1)
        self.assertEqual(gaji.beban_bpjs_jht, 4)
        self.assertEqual(gaji.beban_bjps_jkk, 0)
        self.assertEqual(gaji.persentase_pph21, Decimal('0.00'))
        self.assertEqual(gaji.pot_pph21, 0)
        self.assertEqual(gaji.total_gaji, 9)


class ProsesGajiJobTests(TestCase):
    def setUp(self):
        self.andi = Karyawan.objects.create(
            karyawan_id='1000001', nama='Andi', level=1
        )
        self.budi = Karyawan.objects.create(
            karyawan_id='1000002', nama='Budi', level=1
        )
        self.periode = date(2026, 11, 1)

    def test_progress_updates_between_employees(self):
        job = ProsesGajiJob.objects.create(periode=self.periode)
        seen = []
        real = write_gaji

        def spy(karyawan, periode):
            seen.append(ProsesGajiJob.objects.get(pk=job.pk).processed)
            return real(karyawan, periode)

        with patch('gaji.jobs.write_gaji', side_effect=spy):
            run_proses_gaji(job.pk)

        job.refresh_from_db()
        self.assertEqual(seen, [0, 1])
        self.assertEqual(job.status, StatusProsesGaji.SUCCEEDED)
        self.assertEqual(job.total, 2)
        self.assertEqual(job.processed, 2)
        self.assertEqual(job.message, 'Gaji 2026-11 selesai untuk 2 karyawan.')
        self.assertEqual(Gaji.objects.count(), 2)

    def test_later_failure_keeps_earlier_rows(self):
        job = ProsesGajiJob.objects.create(periode=self.periode)
        real = write_gaji

        def flaky(karyawan, periode):
            if karyawan.pk == self.budi.pk:
                raise RuntimeError('boom')
            return real(karyawan, periode)

        with patch('gaji.jobs.write_gaji', side_effect=flaky):
            run_proses_gaji(job.pk)

        job.refresh_from_db()
        self.assertEqual(job.status, StatusProsesGaji.FAILED)
        self.assertEqual(job.processed, 1)
        self.assertIn('1000002', job.message)
        self.assertTrue(Gaji.objects.filter(karyawan=self.andi).exists())
        self.assertFalse(Gaji.objects.filter(karyawan=self.budi).exists())


class ProsesGajiApiTests(TestCase):
    def setUp(self):
        self.admin = Karyawan.objects.create(
            karyawan_id='0000003', nama='Admin', level=8
        )
        self.admin.refresh_from_db()
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001', nama='Budi', level=1
        )
        self.client = APIClient()
        token = Token.objects.create(user=self.admin.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_post_returns_before_work_and_get_reports_progress(self):
        with patch('gaji.admin_views.enqueue_proses_gaji') as enqueue:
            started = self.client.post(
                '/api/admin/gaji/proses/',
                {'bulan': '2026-11'},
                format='json',
            )

        self.assertEqual(started.status_code, 202)
        self.assertEqual(started.data['status'], StatusProsesGaji.PENDING)
        self.assertEqual(started.data['processed'], 0)
        self.assertEqual(started.data['bulan'], '2026-11')
        self.assertEqual(Gaji.objects.count(), 0)
        enqueue.assert_called_once_with(started.data['id'])

        running = ProsesGajiJob.objects.get(pk=started.data['id'])
        running.status = StatusProsesGaji.RUNNING
        running.total = 340
        running.processed = 12
        running.save(update_fields=['status', 'total', 'processed'])
        polled = self.client.get(f"/api/admin/gaji/proses/{running.pk}/")
        self.assertEqual(polled.status_code, 200)
        self.assertEqual(polled.data['status'], StatusProsesGaji.RUNNING)
        self.assertEqual(polled.data['processed'], 12)
        self.assertEqual(polled.data['total'], 340)

        run_proses_gaji(running.pk)
        done = self.client.get(f"/api/admin/gaji/proses/{running.pk}/")
        self.assertEqual(done.data['status'], StatusProsesGaji.SUCCEEDED)
        self.assertEqual(done.data['processed'], done.data['total'])
        self.assertEqual(done.data['total'], 2)
        self.assertEqual(Gaji.objects.count(), 2)

    def test_second_post_reattaches_to_the_open_job(self):
        job = ProsesGajiJob.objects.create(
            periode=date(2026, 11, 1),
            status=StatusProsesGaji.RUNNING,
            total=10,
            processed=3,
        )
        with patch('gaji.admin_views.enqueue_proses_gaji') as enqueue:
            response = self.client.post(
                '/api/admin/gaji/proses/',
                {'bulan': '2026-11'},
                format='json',
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['id'], job.pk)
        self.assertEqual(response.data['processed'], 3)
        self.assertEqual(ProsesGajiJob.objects.count(), 1)
        enqueue.assert_not_called()

    def test_finished_month_starts_a_new_job(self):
        ProsesGajiJob.objects.create(
            periode=date(2026, 11, 1),
            status=StatusProsesGaji.SUCCEEDED,
        )
        with patch('gaji.admin_views.enqueue_proses_gaji') as enqueue:
            response = self.client.post(
                '/api/admin/gaji/proses/',
                {'bulan': '2026-11'},
                format='json',
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['status'], StatusProsesGaji.PENDING)
        self.assertEqual(ProsesGajiJob.objects.count(), 2)
        enqueue.assert_called_once()

    def test_rejects_bad_bulan_and_non_admin(self):
        bad = self.client.post(
            '/api/admin/gaji/proses/',
            {'bulan': 'November'},
            format='json',
        )
        self.assertEqual(bad.status_code, 400)
        self.assertIn('YYYY-MM', bad.data['detail'])
        self.assertEqual(ProsesGajiJob.objects.count(), 0)

        anonymous = APIClient().post(
            '/api/admin/gaji/proses/',
            {'bulan': '2026-11'},
            format='json',
        )
        self.assertEqual(anonymous.status_code, 401)

        outsider = Karyawan.objects.create(
            karyawan_id='1000009', nama='Tamu', level=1
        )
        outsider.refresh_from_db()
        token = Token.objects.create(user=outsider.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        forbidden = client.post(
            '/api/admin/gaji/proses/',
            {'bulan': '2026-11'},
            format='json',
        )
        self.assertEqual(forbidden.status_code, 403)
        missing = self.client.get('/api/admin/gaji/proses/9999/')
        self.assertEqual(missing.status_code, 404)

    def test_export_csv_lists_every_employee_for_the_month(self):
        empty = self.client.get('/api/admin/gaji/export/', {'bulan': '2026-11'})
        self.assertEqual(empty.status_code, 404)
        self.assertIn('Belum ada gaji', empty.data['detail'])

        ready = self.client.get('/api/admin/gaji/', {'bulan': '2026-11'})
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.data, {'bulan': '2026-11', 'count': 0})

        write_gaji(self.admin, date(2026, 11, 1))
        budi = write_gaji(self.employee, date(2026, 11, 1))
        budi.total_gaji = 123_456
        budi.save(update_fields=['total_gaji'])
        write_gaji(self.employee, date(2026, 10, 1))

        ready = self.client.get('/api/admin/gaji/', {'bulan': '2026-11'})
        self.assertEqual(ready.data['count'], 2)

        response = self.client.get('/api/admin/gaji/export/', {'bulan': '2026-11'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('gaji-2026-11.csv', response['Content-Disposition'])
        rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(
            [row['karyawan_id'] for row in rows],
            ['0000003', '1000001'],
        )
        self.assertEqual(rows[0]['nama'], 'Admin')
        self.assertEqual(rows[1]['nama'], 'Budi')
        self.assertEqual(rows[1]['periode'], '2026-11')
        self.assertEqual(rows[1]['total_gaji'], '123456')
        self.assertEqual(rows[1]['net_penghasilan'], str(budi.net_penghasilan))
        self.assertEqual(rows[1]['ter_status'], budi.ter_status)

        bad = self.client.get('/api/admin/gaji/export/', {'bulan': 'November'})
        self.assertEqual(bad.status_code, 400)
        anonymous = APIClient().get('/api/admin/gaji/export/', {'bulan': '2026-11'})
        self.assertEqual(anonymous.status_code, 401)
