import io
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from absensi.models import Absensi, Kehadiran, StatusKehadiran
from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from dinas.models import Dinas
from gaji.access import GAJI_PASSWORD
from gaji.jobs import run_proses_gaji
from gaji.models import Gaji, ProsesGajiJob, StatusProsesGaji
from gaji.lembur_bayar import UPAH_HARI_LEMBUR, UPAH_JAM_LEMBUR_NUMERATOR
from gaji.services import write_gaji
from gaji.ter import ter_fraction
from karyawan.models import Karyawan, StatusKTk
from koreksi.models import Koreksi, TipeKoreksi
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from lokasi.models import Lokasi
from obat.models import TunjanganObat
from shift.models import HariKerja, Shift


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

    def test_fractional_rupiah_above_a_boundary_uses_the_higher_bracket(self):
        self.assertEqual(ter_fraction('A', Decimal('5400000')), Decimal('0'))
        self.assertEqual(ter_fraction('A', Decimal('5400000.01')), Decimal('0.0025'))
        self.assertEqual(ter_fraction('A', Decimal('5650000')), Decimal('0.0025'))
        self.assertEqual(ter_fraction('A', Decimal('5650000.01')), Decimal('0.005'))

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
            no_bpjs='1234567890123456',
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

        for day in (date(2026, 11, 18), date(2026, 11, 19)):
            Dinas.objects.create(karyawan=self.employee, tanggal=day)
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 21),
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
            tanggal=self.periode,
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ABSENSI,
            nominal=-5_000,
            tanggal=self.periode,
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ADMIN,
            nominal=-10_000,
            tanggal=self.periode,
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ADMIN,
            nominal=-3_000,
            tanggal=self.periode,
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
        # 90 minutes on a recorded day round to 2 hours. 21 November is an
        # approved request with no lokasi and no punch: one hari, zero hours.
        self.assertEqual(gaji.hari_lembur, 1)
        self.assertEqual(gaji.jam_lembur, 2)
        self.assertEqual(gaji.jam_diakumulasi, 0)
        self.assertEqual(gaji.hari_sakit, 2)
        self.assertEqual(gaji.hari_cuti_tahunan, 1)
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
        self.assertEqual(gaji.gaji_lembur, 169_667)
        self.assertEqual(gaji.tunjangan_dinas, 220_000)
        self.assertEqual(gaji.uang_terima_kasih, 0)
        self.assertEqual(gaji.net_penghasilan, 6_145_967)
        self.assertEqual(gaji.persentase_pph21, Decimal('0.75'))
        self.assertEqual(gaji.pot_pph21, 46_095)
        self.assertEqual(gaji.total_gaji, 5_715_572)
        self.assertEqual(gaji.gaji_tambahan, 0)
        self.assertIsNone(gaji.bca_transfer)
        self.assertEqual(
            gaji.total_gaji,
            gaji.net_penghasilan
            - gaji.total_bpjs_benefit
            - gaji.pot_pph21
            - gaji.total_pot_bpjs,
        )

    def test_gaji_tambahan_is_clamped_and_left_out_of_total(self):
        baseline = write_gaji(self.employee, self.periode)
        total = baseline.total_gaji
        net = baseline.net_penghasilan

        self.employee.target_gaji = 6_500_000
        self.employee.bca_transfer = 1_250_000
        self.employee.save(update_fields=['target_gaji', 'bca_transfer'])
        above = write_gaji(self.employee, self.periode)
        self.assertEqual(above.gaji_tambahan, 500_000)
        self.assertEqual(above.bca_transfer, 1_250_000)
        self.assertEqual(above.total_gaji, total)
        self.assertEqual(above.net_penghasilan, net)

        self.employee.target_gaji = 0
        self.employee.save(update_fields=['target_gaji'])
        zero_target = write_gaji(self.employee, self.periode)
        self.assertEqual(zero_target.gaji_tambahan, 0)
        self.assertEqual(zero_target.bca_transfer, 1_250_000)
        self.assertEqual(zero_target.total_gaji, total)

        self.employee.target_gaji = 1_000_000
        self.employee.bca_transfer = None
        self.employee.save(update_fields=['target_gaji', 'bca_transfer'])
        below = write_gaji(self.employee, self.periode)
        self.assertEqual(below.gaji_tambahan, 0)
        self.assertIsNone(below.bca_transfer)
        self.assertEqual(below.total_gaji, total)
        self.assertEqual(below.net_penghasilan, net)

    def test_rerun_deletes_previous_rows_for_that_month(self):
        other_month = write_gaji(self.employee, date(2026, 10, 1))
        first = write_gaji(self.employee, self.periode)
        stray = Gaji.objects.create(
            karyawan=self.employee,
            level=self.employee.level,
            periode=date(2026, 11, 15),
            gaji_lembur=999,
        )
        self.employee.base_gaji = 8_000_000
        self.employee.gaji_bulanan = 7_000_000
        self.employee.lembur_dibayar = False
        self.employee.jabatan = 'Senior'
        self.employee.status_k_tk = StatusKTk.K3
        self.employee.save()

        again = write_gaji(self.employee, self.periode)

        self.assertNotEqual(again.pk, first.pk)
        self.assertFalse(Gaji.objects.filter(pk=first.pk).exists())
        self.assertFalse(Gaji.objects.filter(pk=stray.pk).exists())
        self.assertTrue(Gaji.objects.filter(pk=other_month.pk).exists())
        self.assertEqual(
            Gaji.objects.filter(karyawan=self.employee, periode__year=2026, periode__month=11).count(),
            1,
        )
        self.assertEqual(again.periode, self.periode)
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
        # 10 - 0.5 alpa - 4 employee BPJS, with the fractional benefit added
        # and removed. Rounding that result once is 6; subtracting the
        # rounded columns is 5.
        self.assertEqual(gaji.total_gaji, 6)
        self.assertEqual(
            gaji.net_penghasilan
            - gaji.total_bpjs_benefit
            - gaji.pot_pph21
            - gaji.total_pot_bpjs,
            5,
        )

    def test_pph_includes_tunjangan_dinas_before_any_rounding(self):
        self.employee.base_gaji = 100
        self.employee.gaji_bulanan = 5_539_996
        self.employee.save(update_fields=['base_gaji', 'gaji_bulanan'])
        Dinas.objects.create(karyawan=self.employee, tanggal=date(2026, 11, 2))
        TunjanganObat.objects.create(
            karyawan=self.employee, nominal=1, bulan=self.periode
        )
        Koreksi.objects.create(
            karyawan=self.employee,
            tipe=TipeKoreksi.ABSENSI,
            nominal=-1,
            tanggal=self.periode,
        )

        gaji = write_gaji(self.employee, self.periode)

        # Exact net is 5,539,996 + 4.54 benefit + 110,000 dinas + 1 obat - 1 koreksi
        # = 5,650,000.54. That sits in the 0.50% bracket. Rounding the benefit
        # to 4 first would leave 5,650,000 and the 0.25% bracket.
        self.assertEqual(gaji.tunjangan_dinas, 110_000)
        self.assertEqual(gaji.tunjangan_obat, 1)
        self.assertEqual(gaji.koreksi_absensi, -1)
        self.assertEqual(gaji.persentase_pph21, Decimal('0.50'))
        self.assertEqual(gaji.pot_pph21, 28_250)
        self.assertEqual(gaji.total_gaji, 5_621_742)

    def test_absensi_dihitung_false_skips_pot_alpa(self):
        self.employee.absensi_dihitung = False
        self.employee.no_bpjs = ''
        self.employee.save(update_fields=['absensi_dihitung', 'no_bpjs'])
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusKehadiran.ALPA,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 3),
            status=StatusKehadiran.ALPA,
        )

        gaji = write_gaji(self.employee, self.periode)

        self.assertEqual(gaji.hari_alpa, 2)
        self.assertEqual(gaji.pot_alpa, 0)
        self.assertEqual(gaji.net_penghasilan, 6_000_000)

    def test_jp_is_zero_when_completed_age_is_above_60(self):
        self.employee.tanggal_lahir = date(1965, 11, 30)
        self.employee.save(update_fields=['tanggal_lahir'])

        gaji = write_gaji(self.employee, self.periode)

        self.assertEqual(gaji.pot_bpjs_jp, 0)
        self.assertEqual(gaji.beban_bpjs_jp, 0)
        self.assertEqual(gaji.pot_bpjs_jht, 90_000)
        self.assertEqual(gaji.beban_bpjs_jht, 166_500)
        self.assertEqual(gaji.pot_bpjs_kesehatan, 45_000)

    def test_jp_still_applies_at_age_60_and_without_a_birth_date(self):
        self.employee.tanggal_lahir = date(1966, 11, 30)
        self.employee.save(update_fields=['tanggal_lahir'])

        at_60 = write_gaji(self.employee, self.periode)

        self.assertEqual(at_60.pot_bpjs_jp, 45_000)
        self.assertEqual(at_60.beban_bpjs_jp, 90_000)

        self.employee.tanggal_lahir = date(1965, 12, 1)
        self.employee.save(update_fields=['tanggal_lahir'])

        turns_61_next_month = write_gaji(self.employee, self.periode)

        self.assertEqual(turns_61_next_month.pot_bpjs_jp, 45_000)
        self.assertEqual(turns_61_next_month.beban_bpjs_jp, 90_000)

        self.employee.tanggal_lahir = None
        self.employee.save(update_fields=['tanggal_lahir'])

        unknown = write_gaji(self.employee, self.periode)

        self.assertEqual(unknown.pot_bpjs_jp, 45_000)
        self.assertEqual(unknown.beban_bpjs_jp, 90_000)

    def test_blank_no_bpjs_skips_bpjs_and_pph(self):
        self.employee.no_bpjs = '   '
        self.employee.save(update_fields=['no_bpjs'])

        gaji = write_gaji(self.employee, self.periode)

        self.assertEqual(gaji.total_pot_bpjs, 0)
        self.assertEqual(gaji.total_bpjs_benefit, 0)
        self.assertEqual(gaji.beban_bpjs_jht, 0)
        self.assertEqual(gaji.beban_bpjs_jp, 0)
        self.assertEqual(gaji.pot_bpjs_kesehatan, 0)
        self.assertEqual(gaji.persentase_pph21, Decimal('0.00'))
        self.assertEqual(gaji.pot_pph21, 0)
        self.assertEqual(gaji.net_penghasilan, 6_000_000)
        self.assertEqual(gaji.total_gaji, gaji.net_penghasilan)

    def test_scheduled_weekday_overtime_is_hours_only(self):
        lokasi = Lokasi.objects.create(id='80', nama='Toko')
        self.employee.lokasi_kerja = lokasi
        self.employee.save(update_fields=['lokasi_kerja'])
        Shift.objects.create(
            lokasi_kerja=lokasi,
            hari=HariKerja.SENIN,
            jam_masuk=time(8, 0),
            jam_keluar=time(17, 0),
        )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusPermohonanLembur.APPROVED,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 2),
            status=StatusKehadiran.HADIR,
            lembur=60,
        )

        gaji = write_gaji(self.employee, self.periode)

        self.assertEqual(gaji.hari_lembur, 0)
        self.assertEqual(gaji.jam_lembur, 1)
        self.assertEqual(gaji.gaji_lembur, 18_333)
        self.assertEqual(gaji.jam_diakumulasi, 0)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.akumulasi_lembur, 0)

    def test_off_day_and_liburan_pay_hours_and_a_flat_day(self):
        lokasi = Lokasi.objects.create(id='80', nama='Toko')
        self.employee.lokasi_kerja = lokasi
        self.employee.save(update_fields=['lokasi_kerja'])
        Shift.objects.create(
            lokasi_kerja=lokasi,
            hari=HariKerja.SENIN,
            jam_masuk=time(8, 0),
            jam_keluar=time(17, 0),
        )
        Liburan.objects.create(nama='Maulid', tanggal=date(2026, 11, 9))
        for day, hours in ((date(2026, 11, 7), 3), (date(2026, 11, 9), 3)):
            PermohonanLembur.objects.create(
                karyawan=self.employee,
                tanggal=day,
                status=StatusPermohonanLembur.APPROVED,
            )
            Absensi.objects.create(
                karyawan=self.employee,
                lokasi=lokasi,
                tanggal=day,
                jam_masuk=time(8, 0),
                durasi=timedelta(hours=hours),
            )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 7),
            status=StatusPermohonanLembur.APPROVED,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 9),
            status=StatusKehadiran.HADIR,
            lembur=999,
        )
        PermohonanLembur.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 14),
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        Absensi.objects.create(
            karyawan=self.employee,
            lokasi=lokasi,
            tanggal=date(2026, 11, 14),
            jam_masuk=time(8, 0),
            durasi=timedelta(hours=5),
        )

        gaji = write_gaji(self.employee, self.periode)

        self.assertEqual(gaji.hari_lembur, 2)
        self.assertEqual(gaji.jam_lembur, 6)
        self.assertEqual(
            gaji.gaji_lembur,
            UPAH_JAM_LEMBUR_NUMERATOR + 2 * UPAH_HARI_LEMBUR,
        )

    def test_unpaid_hours_bank_once_and_a_reprocess_replaces_them(self):
        self.employee.lembur_dibayar = False
        self.employee.akumulasi_lembur = 10
        self.employee.save(update_fields=['lembur_dibayar', 'akumulasi_lembur'])
        row = Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 3),
            status=StatusKehadiran.HADIR,
            lembur=90,
        )
        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 10, 5),
            status=StatusKehadiran.HADIR,
            lembur=60,
        )

        write_gaji(self.employee, date(2026, 10, 1))
        first = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(first.gaji_lembur, 0)
        self.assertEqual(first.jam_lembur, 2)
        self.assertEqual(first.jam_diakumulasi, 2)
        self.assertEqual(self.employee.akumulasi_lembur, 13)

        again = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(again.jam_diakumulasi, 2)
        self.assertEqual(self.employee.akumulasi_lembur, 13)

        row.lembur = 150
        row.save(update_fields=['lembur'])
        changed = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(changed.jam_lembur, 3)
        self.assertEqual(changed.jam_diakumulasi, 3)
        self.assertEqual(self.employee.akumulasi_lembur, 14)

        self.employee.lembur_dibayar = True
        self.employee.save(update_fields=['lembur_dibayar'])
        paid = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(paid.gaji_lembur, 55_000)
        self.assertEqual(paid.jam_diakumulasi, 0)
        self.assertEqual(self.employee.akumulasi_lembur, 11)
        october_gaji = Gaji.objects.get(
            karyawan=self.employee, periode=date(2026, 10, 1)
        )
        self.assertEqual(october_gaji.jam_diakumulasi, 1)

    def test_sixty_late_minutes_remove_one_annual_leave_once(self):
        self.employee.cuti_tahunan = 5
        self.employee.save(update_fields=['cuti_tahunan'])
        late = Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 11, 3),
            status=StatusKehadiran.HADIR,
            menit_telat=59,
        )

        below = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(below.total_menit_telat, 59)
        self.assertEqual(below.cuti_tahunan_dikurangi, 0)
        self.assertEqual(self.employee.cuti_tahunan, 5)

        late.menit_telat = 60
        late.save(update_fields=['menit_telat'])
        at_threshold = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(at_threshold.cuti_tahunan_dikurangi, 1)
        self.assertEqual(self.employee.cuti_tahunan, 4)

        again = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(again.cuti_tahunan_dikurangi, 1)
        self.assertEqual(self.employee.cuti_tahunan, 4)

        late.menit_telat = 120
        late.save(update_fields=['menit_telat'])
        still_one = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(still_one.total_menit_telat, 120)
        self.assertEqual(still_one.cuti_tahunan_dikurangi, 1)
        self.assertEqual(self.employee.cuti_tahunan, 4)

        late.menit_telat = 59
        late.save(update_fields=['menit_telat'])
        restored = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(restored.cuti_tahunan_dikurangi, 0)
        self.assertEqual(self.employee.cuti_tahunan, 5)

        Kehadiran.objects.create(
            karyawan=self.employee,
            tanggal=date(2026, 10, 5),
            status=StatusKehadiran.HADIR,
            menit_telat=60,
        )
        october = write_gaji(self.employee, date(2026, 10, 1))
        self.employee.refresh_from_db()
        self.assertEqual(october.cuti_tahunan_dikurangi, 1)
        self.assertEqual(self.employee.cuti_tahunan, 4)
        write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.cuti_tahunan, 4)

        self.employee.cuti_tahunan = 0
        self.employee.save(update_fields=['cuti_tahunan'])
        late.menit_telat = 60
        late.save(update_fields=['menit_telat'])
        empty = write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(empty.cuti_tahunan_dikurangi, 0)
        self.assertEqual(self.employee.cuti_tahunan, 0)
        write_gaji(self.employee, self.periode)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.cuti_tahunan, 0)


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

    def test_second_run_overwrites_the_same_month(self):
        first = ProsesGajiJob.objects.create(periode=self.periode)
        run_proses_gaji(first.pk)
        self.andi.base_gaji = 4_000_000
        self.andi.gaji_bulanan = 5_000_000
        self.andi.save()
        andi_row = Gaji.objects.get(karyawan=self.andi, periode=self.periode)
        andi_row.gaji_lembur = 999
        andi_row.save(update_fields=['gaji_lembur'])

        second = ProsesGajiJob.objects.create(periode=self.periode)
        run_proses_gaji(second.pk)

        self.assertFalse(Gaji.objects.filter(pk=andi_row.pk).exists())
        self.assertEqual(Gaji.objects.filter(periode=self.periode).count(), 2)
        row = Gaji.objects.get(karyawan=self.andi, periode=self.periode)
        self.assertEqual(Gaji.objects.filter(karyawan=self.andi).count(), 1)
        self.assertEqual(row.base_gaji_bpjs, 4_000_000)
        self.assertEqual(row.gaji_bulanan, 5_000_000)
        self.assertEqual(row.gaji_lembur, 0)

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
        self.token = token
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {token.key}',
            HTTP_X_GAJI_PASSWORD=GAJI_PASSWORD,
        )

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
        client.credentials(
            HTTP_AUTHORIZATION=f'Token {token.key}',
            HTTP_X_GAJI_PASSWORD=GAJI_PASSWORD,
        )
        forbidden = client.post(
            '/api/admin/gaji/proses/',
            {'bulan': '2026-11'},
            format='json',
        )
        self.assertEqual(forbidden.status_code, 403)
        missing = self.client.get('/api/admin/gaji/proses/9999/')
        self.assertEqual(missing.status_code, 404)

    def test_export_bank_transfer_lists_every_employee_for_the_month(self):
        empty = self.client.get('/api/admin/gaji/export/', {'bulan': '2026-11'})
        self.assertEqual(empty.status_code, 404)
        self.assertIn('Belum ada gaji', empty.data['detail'])

        ready = self.client.get('/api/admin/gaji/', {'bulan': '2026-11'})
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.data, {'bulan': '2026-11', 'count': 0})

        self.admin.no_bpjs = '   '
        self.admin.jabatan = 'HR'
        self.admin.gaji_bulanan = 1_000_000
        self.admin.target_gaji = 1_250_000
        self.admin.tanggal_awal = date(2020, 1, 15)
        self.admin.tanggal_keluar = date(2024, 1, 14)
        self.admin.save()
        self.employee.jabatan = 'Staff'
        self.employee.percobaan_jabatan = True
        self.employee.tanggal_awal = date(2018, 6, 1)
        self.employee.tanggal_lahir = date(1990, 12, 1)
        self.employee.no_bpjs = '1234567890123456'
        self.employee.no_kpj = '10000740943'
        self.employee.target_gaji = 2_000_000
        self.employee.status_k_tk = StatusKTk.K1
        self.employee.save()

        admin_gaji = write_gaji(self.admin, date(2026, 11, 1))
        budi = write_gaji(self.employee, date(2026, 11, 1))
        budi.total_gaji = 123_456
        budi.save(update_fields=['total_gaji'])
        write_gaji(self.employee, date(2026, 10, 1))

        ready = self.client.get('/api/admin/gaji/', {'bulan': '2026-11'})
        self.assertEqual(ready.data['count'], 2)

        response = self.client.get('/api/admin/gaji/export/', {'bulan': '2026-11'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml.sheet', response['Content-Type'])
        self.assertIn(
            'Bank-Transfer-11-2026.xlsx', response['Content-Disposition']
        )
        wb = load_workbook(io.BytesIO(response.content))
        ws = wb['Bank Transfer']
        self.assertEqual(ws.max_row, 4)
        self.assertEqual(ws.freeze_panes, 'A3')
        self.assertEqual(ws.auto_filter.ref, 'A2:AQ4')
        self.assertEqual(
            [ws.cell(row, 1).value for row in range(3, 5)],
            ['0000003', '1000001'],
        )

        before = [
            'ID Karyawan',
            'Nama',
            'Level',
            'Jabatan',
            'Percobaan Jabatan',
            'Lama Kerja',
            'Umur',
            'No. BPJS',
            'No. KPJ',
            'Hadir',
            'Sakit',
            'Cuti Tahunan',
            'Cuti Tambahan',
            'Alpa',
            'Jam Lembur',
            'Hari Lembur',
            'Lembur Perjalanan Dinas',
            'Gaji BPJS',
        ]
        potongan = ['Kesehatan', 'JHT', 'JP']
        beban = ['Kesehatan', 'JHT', 'JP', 'JKM', 'JKK']
        after = [
            'Gaji Bulanan',
            'Gaji Lembur',
            'Tunjangan Obat',
            'Tunjangan Dinas',
            'Potongan Alpa',
            'Koreksi Absensi',
            'Koreksi Admin',
            'Uang Terima Kasih',
            'Net Penghasilan dikena Pajak',
            'Status K/TK',
            'Status TER',
            'Persentase PPH21',
            'Potongan PPH21',
            'Total Gaji',
            'Gaji Tambahan',
            'Transfer PT',
            'Transfer HO',
        ]
        row1 = (
            before
            + ['Potongan BPJS', None, None]
            + ['Beban BPJS Perusahaan', None, None, None, None]
            + after
        )
        row2 = (
            [None] * len(before)
            + potongan
            + beban
            + [None] * len(after)
        )
        self.assertEqual(
            [ws.cell(1, col).value for col in range(1, 44)],
            row1,
        )
        self.assertEqual(
            [ws.cell(2, col).value for col in range(1, 44)],
            row2,
        )
        merged = {str(item) for item in ws.merged_cells.ranges}
        vertical = [
            f'{get_column_letter(col)}1:{get_column_letter(col)}2'
            for col in list(range(1, len(before) + 1))
            + list(range(len(before) + len(potongan) + len(beban) + 1, 44))
        ]
        self.assertEqual(merged, set(vertical) | {'S1:U1', 'V1:Z1'})
        self.assertEqual(ws['A1'].alignment.horizontal, 'center')
        self.assertEqual(ws['A1'].border.left.style, 'thin')
        self.assertTrue(str(ws['A1'].fill.fgColor.rgb).endswith('D6DCE4'))
        self.assertTrue(str(ws['S1'].fill.fgColor.rgb).endswith('F8CBAD'))
        self.assertTrue(str(ws['V1'].fill.fgColor.rgb).endswith('C6EFCE'))

        columns = []
        for col in range(1, 44):
            top = ws.cell(1, col).value
            sub = ws.cell(2, col).value
            if sub is None:
                columns.append((None, top))
                continue
            group = top
            look = col
            while group is None:
                look -= 1
                group = ws.cell(1, look).value
            columns.append((group, sub))

        def row_for(karyawan_id):
            for row in range(3, 5):
                if ws.cell(row, 1).value == karyawan_id:
                    return {
                        columns[col - 1]: ws.cell(row, col).value
                        for col in range(1, 44)
                    }
            self.fail(karyawan_id)

        admin = row_for('0000003')
        staff = row_for('1000001')
        self.assertEqual(admin[(None, 'Nama')], 'Admin')
        self.assertEqual(admin[(None, 'Level')], 8)
        self.assertEqual(admin[(None, 'Jabatan')], 'HR')
        self.assertEqual(admin[(None, 'Percobaan Jabatan')], 'Tidak')
        self.assertEqual(admin[(None, 'Lama Kerja')], 3)
        self.assertIsNone(admin[(None, 'Umur')])
        self.assertIsNone(admin[(None, 'No. BPJS')])
        self.assertEqual(admin[(None, 'Gaji Tambahan')], 250_000)
        self.assertGreater(admin_gaji.total_gaji, 0)
        self.assertEqual(admin[(None, 'Transfer PT')], 0)
        self.assertEqual(
            admin[(None, 'Transfer HO')],
            admin_gaji.total_gaji + 250_000,
        )
        self.assertEqual(ws['A3'].number_format, '@')

        self.assertEqual(staff[(None, 'Nama')], 'Budi')
        self.assertEqual(staff[(None, 'Jabatan')], 'Staff')
        self.assertEqual(staff[(None, 'Percobaan Jabatan')], 'Ya')
        self.assertEqual(staff[(None, 'Lama Kerja')], 8)
        self.assertEqual(staff[(None, 'Umur')], 35)
        self.assertEqual(staff[(None, 'No. BPJS')], '1234567890123456')
        self.assertEqual(staff[(None, 'No. KPJ')], '10000740943')
        self.assertEqual(staff[(None, 'Lembur Perjalanan Dinas')], budi.hari_dinas)
        self.assertEqual(
            staff[('Potongan BPJS', 'Kesehatan')], budi.pot_bpjs_kesehatan
        )
        self.assertEqual(staff[('Potongan BPJS', 'JHT')], budi.pot_bpjs_jht)
        self.assertEqual(staff[('Potongan BPJS', 'JP')], budi.pot_bpjs_jp)
        self.assertEqual(
            staff[('Beban BPJS Perusahaan', 'JKK')], budi.beban_bjps_jkk
        )
        self.assertEqual(
            staff[(None, 'Net Penghasilan dikena Pajak')], budi.net_penghasilan
        )
        self.assertEqual(staff[(None, 'Status K/TK')], StatusKTk.K1)
        self.assertEqual(staff[(None, 'Status TER')], budi.ter_status)
        self.assertEqual(staff[(None, 'Total Gaji')], 123_456)
        self.assertEqual(staff[(None, 'Gaji Tambahan')], 2_000_000)
        self.assertEqual(staff[(None, 'Transfer PT')], 123_456)
        self.assertEqual(staff[(None, 'Transfer HO')], 2_000_000)
        total_col = columns.index((None, 'Total Gaji')) + 1
        percent_col = columns.index((None, 'Persentase PPH21')) + 1
        self.assertEqual(
            ws.cell(4, total_col).number_format, '#,##0'
        )
        self.assertEqual(ws.cell(4, percent_col).number_format, '0.00')

        bad = self.client.get('/api/admin/gaji/export/', {'bulan': 'November'})
        self.assertEqual(bad.status_code, 400)
        anonymous = APIClient().get('/api/admin/gaji/export/', {'bulan': '2026-11'})
        self.assertEqual(anonymous.status_code, 401)

    def test_karyawan_list_returns_wage_fields_for_every_employee(self):
        self.admin.jabatan = 'HR'
        self.admin.no_bpjs = '111'
        self.admin.base_gaji = 1_000_000
        self.admin.gaji_bulanan = 2_000_000
        self.admin.save()
        self.employee.jabatan = 'Staff'
        self.employee.no_bpjs = ''
        self.employee.base_gaji = 4_500_000
        self.employee.gaji_bulanan = 6_000_000
        self.employee.target_gaji = 8_000_000
        self.employee.bca_transfer = 100_000
        self.employee.lembur_dibayar = True
        self.employee.save()

        locked = APIClient()
        locked.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        denied = locked.get('/api/admin/gaji/karyawan/')
        self.assertEqual(denied.status_code, 403)

        response = self.client.get('/api/admin/gaji/karyawan/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [
                {
                    'karyawan_id': '0000003',
                    'nama': 'Admin',
                    'level': 8,
                    'jabatan': 'HR',
                    'no_bpjs': '111',
                    'base_gaji': 1_000_000,
                    'gaji_bulanan': 2_000_000,
                    'target_gaji': None,
                    'bca_transfer': None,
                    'absensi_dihitung': True,
                    'lembur_dibayar': False,
                },
                {
                    'karyawan_id': '1000001',
                    'nama': 'Budi',
                    'level': 1,
                    'jabatan': 'Staff',
                    'no_bpjs': '',
                    'base_gaji': 4_500_000,
                    'gaji_bulanan': 6_000_000,
                    'target_gaji': 8_000_000,
                    'bca_transfer': 100_000,
                    'absensi_dihitung': True,
                    'lembur_dibayar': True,
                },
            ],
        )

    def test_patch_absensi_dihitung_for_one_employee(self):
        response = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'absensi_dihitung': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['karyawan_id'], '1000001')
        self.assertFalse(response.data['absensi_dihitung'])
        self.employee.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertFalse(self.employee.absensi_dihitung)
        self.assertFalse(self.employee.lembur_dibayar)
        self.assertTrue(self.admin.absensi_dihitung)

        bad = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'absensi_dihitung': 'false'},
            format='json',
        )
        self.assertEqual(bad.status_code, 400)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.absensi_dihitung)

        missing = self.client.patch(
            '/api/admin/gaji/karyawan/9999999/',
            {'absensi_dihitung': True},
            format='json',
        )
        self.assertEqual(missing.status_code, 404)

        locked = APIClient()
        locked.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        denied = locked.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'absensi_dihitung': True},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

    def test_patch_updates_any_gaji_karyawan_field(self):
        self.employee.base_gaji = 1
        self.employee.gaji_bulanan = 2
        self.employee.absensi_dihitung = True
        self.employee.save()

        response = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {
                'nama': '  Budi Santoso ',
                'level': 9,
                'jabatan': 'J' * 128,
                'no_bpjs': '1' * 16,
                'base_gaji': 7_000_000,
                'gaji_bulanan': 8_000_000,
                'absensi_dihitung': False,
                'lembur_dibayar': True,
                'password': GAJI_PASSWORD,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nama'], 'Budi Santoso')
        self.assertEqual(response.data['level'], 9)
        self.assertEqual(response.data['jabatan'], 'J' * 128)
        self.assertEqual(response.data['no_bpjs'], '1' * 16)
        self.assertEqual(response.data['base_gaji'], 7_000_000)
        self.assertEqual(response.data['gaji_bulanan'], 8_000_000)
        self.assertFalse(response.data['absensi_dihitung'])
        self.assertTrue(response.data['lembur_dibayar'])

        self.employee.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.employee.nama, 'Budi Santoso')
        self.assertEqual(self.employee.level, 9)
        self.assertEqual(self.employee.base_gaji, 7_000_000)
        self.assertTrue(self.employee.lembur_dibayar)
        self.assertFalse(self.admin.lembur_dibayar)
        self.assertEqual(self.admin.nama, 'Admin')
        self.assertEqual(self.admin.level, 8)

        one_field = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'jabatan': '  '},
            format='json',
        )
        self.assertEqual(one_field.status_code, 200)
        self.assertEqual(one_field.data['jabatan'], '')
        self.assertEqual(one_field.data['nama'], 'Budi Santoso')
        self.assertEqual(one_field.data['base_gaji'], 7_000_000)
        self.assertFalse(one_field.data['absensi_dihitung'])
        self.assertTrue(one_field.data['lembur_dibayar'])

        boundaries = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'level': 0, 'no_bpjs': '', 'base_gaji': 0, 'gaji_bulanan': 0},
            format='json',
        )
        self.assertEqual(boundaries.status_code, 200)
        self.assertEqual(boundaries.data['level'], 0)
        self.assertEqual(boundaries.data['no_bpjs'], '')
        self.assertEqual(boundaries.data['base_gaji'], 0)
        self.assertEqual(boundaries.data['gaji_bulanan'], 0)

    def test_patch_sets_and_clears_nullable_wage_fields(self):
        self.employee.target_gaji = 1
        self.employee.bca_transfer = 2
        self.employee.save(update_fields=['target_gaji', 'bca_transfer'])

        response = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'target_gaji': 9_000_000, 'bca_transfer': None},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['target_gaji'], 9_000_000)
        self.assertIsNone(response.data['bca_transfer'])
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.target_gaji, 9_000_000)
        self.assertIsNone(self.employee.bca_transfer)

        cleared = self.client.patch(
            '/api/admin/gaji/karyawan/1000001/',
            {'target_gaji': None},
            format='json',
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.data['target_gaji'])
        self.assertIsNone(cleared.data['bca_transfer'])
        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.target_gaji)
        self.assertIsNone(self.employee.bca_transfer)

    def test_patch_rejects_invalid_gaji_karyawan_fields(self):
        self.employee.jabatan = 'Staff'
        self.employee.base_gaji = 4_500_000
        self.employee.lembur_dibayar = True
        self.employee.save()
        invalid = [
            {},
            {'password': GAJI_PASSWORD},
            {'nama': '   '},
            {'nama': 1},
            {'level': 10},
            {'level': -1},
            {'level': True},
            {'level': '1'},
            {'jabatan': 'x' * 129},
            {'no_bpjs': '1' * 17},
            {'base_gaji': -1},
            {'base_gaji': True},
            {'base_gaji': 1.5},
            {'base_gaji': 1 << 63},
            {'gaji_bulanan': -5},
            {'target_gaji': -1},
            {'target_gaji': True},
            {'target_gaji': 1.5},
            {'target_gaji': 1 << 63},
            {'bca_transfer': -1},
            {'bca_transfer': '100'},
            {'absensi_dihitung': 'false'},
            {'lembur_dibayar': 'false'},
            {'lembur_dibayar': 1},
            {'karyawan_id': '1000002'},
            {'nama': 'Sari', 'level': 99},
        ]
        for payload in invalid:
            response = self.client.patch(
                '/api/admin/gaji/karyawan/1000001/',
                payload,
                format='json',
            )
            self.assertEqual(response.status_code, 400, payload)
            self.assertTrue(response.data['detail'], payload)

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.nama, 'Budi')
        self.assertEqual(self.employee.level, 1)
        self.assertEqual(self.employee.jabatan, 'Staff')
        self.assertEqual(self.employee.base_gaji, 4_500_000)
        self.assertTrue(self.employee.absensi_dihitung)
        self.assertTrue(self.employee.lembur_dibayar)

    def test_module_password_required_for_any_admin(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        missing = client.post(
            '/api/admin/gaji/proses/',
            {'bulan': '2026-11'},
            format='json',
        )
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.data['detail'], 'Kata sandi Gaji tidak valid.')
        self.assertEqual(ProsesGajiJob.objects.count(), 0)

        wrong = client.get(
            '/api/admin/gaji/export/',
            {'bulan': '2026-11', 'password': 'wrong'},
        )
        self.assertEqual(wrong.status_code, 403)

        with patch('gaji.admin_views.enqueue_proses_gaji') as enqueue:
            via_body = client.post(
                '/api/admin/gaji/proses/',
                {'bulan': '2026-11', 'password': GAJI_PASSWORD},
                format='json',
            )
        self.assertEqual(via_body.status_code, 202)
        self.assertEqual(ProsesGajiJob.objects.count(), 1)
        enqueue.assert_called_once()
