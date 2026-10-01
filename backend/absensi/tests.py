from datetime import date, datetime, time, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from absensi.kehadiran import proses_kehadiran
from absensi.models import Absensi, Kehadiran, RekapAbsensi, StatusKehadiran
from absensi.proses import proses_absensi_bulan
from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from karyawan.models import Karyawan
from lembur.models import PermohonanLembur, StatusPermohonanLembur
from liburan.models import Liburan
from lokasi.models import Lokasi
from shift.models import HariKerja, Shift

MONTH = date(2026, 9, 1)
_HARI_BY_WEEKDAY = [
    HariKerja.SENIN,
    HariKerja.SELASA,
    HariKerja.RABU,
    HariKerja.KAMIS,
    HariKerja.JUMAT,
    HariKerja.SABTU,
    HariKerja.MINGGU,
]


def _days_in_month(weekday: int) -> list[date]:
    days = []
    current = MONTH
    while current.month == MONTH.month:
        if current.weekday() == weekday:
            days.append(current)
        current += timedelta(days=1)
    return days


def _karyawan(karyawan_id, nama, lokasi):
    return Karyawan.objects.create(
        karyawan_id=karyawan_id,
        nama=nama,
        lokasi_kerja=lokasi,
        level=1,
    )


def _shift(lokasi, weekday, masuk, keluar):
    return Shift.objects.create(
        lokasi_kerja=lokasi,
        hari=_HARI_BY_WEEKDAY[weekday],
        jam_masuk=time.fromisoformat(masuk),
        jam_keluar=time.fromisoformat(keluar),
    )


def _punch(karyawan, lokasi, tanggal, masuk, keluar):
    masuk_t = time.fromisoformat(masuk)
    keluar_t = time.fromisoformat(keluar)
    start = datetime.combine(tanggal, masuk_t)
    end = datetime.combine(tanggal, keluar_t)
    if end <= start:
        end += timedelta(days=1)
    return Absensi.objects.create(
        karyawan=karyawan,
        lokasi=lokasi,
        tanggal=tanggal,
        jam_masuk=masuk_t,
        durasi=end - start,
    )


def _cuti(karyawan, tipe, tanggal, status=StatusPermohonanCuti.APPROVED):
    permohonan = PermohonanCuti.objects.create(
        karyawan=karyawan,
        tipe=tipe,
        tanggal_mulai=tanggal,
        tanggal_selesai=tanggal,
        status=status,
    )
    return Cuti.objects.create(permohonan=permohonan, tanggal=tanggal)


def _notes(rekap, tanggal):
    return [row.pesan for row in rekap.catatan.all() if row.tanggal == tanggal]


class ProsesAbsensiTests(TestCase):
    def setUp(self):
        self.home = Lokasi.objects.create(id='81', nama='Toko 81')
        self.other = Lokasi.objects.create(id='99', nama='Toko 99')
        self.karyawan = _karyawan('1000001', 'Budi', self.home)
        # Tuesday 2026-09-01, and every other Tuesday that month.
        self.workday = 1
        self.scheduled = _days_in_month(self.workday)
        self.focus = self.scheduled[0]
        _shift(self.home, self.workday, '08:00', '17:00')
        # Different hours at the punch location must not be used.
        _shift(self.other, self.workday, '09:00', '18:00')

    def _rekap(self):
        rows = proses_absensi_bulan(MONTH)
        return next(row for row in rows if row.karyawan_id == self.karyawan.karyawan_id)

    def test_cross_location_on_time_uses_home_shift(self):
        _punch(self.karyawan, self.other, self.focus, '08:30', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.hari_telat, 1)
        self.assertEqual(rekap.total_menit_telat, 30)
        self.assertEqual(rekap.hari_alpa, len(self.scheduled) - 1)
        self.assertEqual(rekap.hari_keluar_cepat, 0)
        self.assertEqual(rekap.total_menit_lembur, 0)
        self.assertEqual(
            _notes(rekap, self.focus),
            ['Telat 30 menit. Jadwal masuk 08:00, absen masuk 08:30.'],
        )

    def test_on_time_at_other_location_has_no_penalty(self):
        _punch(self.karyawan, self.other, self.focus, '08:00', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.hari_telat, 0)
        self.assertEqual(rekap.total_menit_telat, 0)
        self.assertEqual(_notes(rekap, self.focus), [])

    def test_alpa_when_shift_exists_and_no_punch(self):
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 0)
        self.assertEqual(rekap.hari_alpa, len(self.scheduled))
        self.assertEqual(
            _notes(rekap, self.focus),
            ['Tidak hadir (alpa). Jadwal shift 08:00–17:00.'],
        )

    def test_day_without_home_shift_is_not_alpa(self):
        sunday = _days_in_month(6)[0]
        _punch(self.karyawan, self.other, sunday, '08:00', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 0)
        self.assertEqual(_notes(rekap, sunday), [])
        self.assertNotIn(sunday, [row.tanggal for row in rekap.catatan.all()])

    def test_approved_cuti_and_liburan_remove_obligation(self):
        _cuti(self.karyawan, TipeCuti.SAKIT, self.focus)
        holiday = self.scheduled[1]
        Liburan.objects.create(nama='Libur Toko', tanggal=holiday)
        rekap = self._rekap()
        excused = 2
        self.assertEqual(rekap.hari_alpa, len(self.scheduled) - excused)
        self.assertEqual(rekap.hari_hadir, 0)
        self.assertEqual(_notes(rekap, self.focus), [])
        self.assertEqual(_notes(rekap, holiday), [])

    def test_pending_cuti_does_not_excuse_alpa(self):
        _cuti(
            self.karyawan,
            TipeCuti.IZIN_OFF,
            self.focus,
            status=StatusPermohonanCuti.MENUNGGU_HRD,
        )
        rekap = self._rekap()
        self.assertEqual(rekap.hari_alpa, len(self.scheduled))
        self.assertIn('Tidak hadir (alpa)', _notes(rekap, self.focus)[0])

    def test_izin_telat_clears_lateness(self):
        _punch(self.karyawan, self.home, self.focus, '08:20', '17:00')
        _cuti(self.karyawan, TipeCuti.IZIN_TELAT, self.focus)
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.hari_telat, 0)
        self.assertEqual(rekap.total_menit_telat, 0)
        self.assertEqual(_notes(rekap, self.focus), [])

    def test_pulang_cepat_and_izin(self):
        _punch(self.karyawan, self.home, self.focus, '08:00', '16:40')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.hari_keluar_cepat, 1)
        self.assertEqual(
            _notes(rekap, self.focus),
            ['Pulang lebih cepat 20 menit. Jadwal keluar 17:00, absen keluar 16:40.'],
        )

        _cuti(self.karyawan, TipeCuti.IZIN_PULANG_CEPAT, self.focus)
        rekap = self._rekap()
        self.assertEqual(rekap.hari_keluar_cepat, 0)
        self.assertEqual(_notes(rekap, self.focus), [])

    def test_lembur_minutes_only_when_approved(self):
        _punch(self.karyawan, self.home, self.focus, '08:00', '17:45')
        PermohonanLembur.objects.create(
            karyawan=self.karyawan,
            tanggal=self.focus,
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        rekap = self._rekap()
        self.assertEqual(rekap.total_menit_lembur, 0)
        self.assertEqual(rekap.hari_hadir, 1)

        PermohonanLembur.objects.filter(karyawan=self.karyawan).update(
            status=StatusPermohonanLembur.APPROVED
        )
        rekap = self._rekap()
        self.assertEqual(rekap.total_menit_lembur, 45)
        self.assertEqual(_notes(rekap, self.focus), [])

    def test_best_match_picks_closest_start_and_notes_unused_punches(self):
        _punch(self.karyawan, self.other, self.focus, '07:00', '08:00')
        _punch(self.karyawan, self.other, self.focus, '08:05', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_telat, 1)
        self.assertEqual(rekap.total_menit_telat, 5)
        self.assertEqual(
            _notes(rekap, self.focus),
            [
                'Telat 5 menit. Jadwal masuk 08:00, absen masuk 08:05.',
                'Dipakai absen masuk 08:05 di lokasi 99. 1 entri lain pada hari ini tidak dipakai.',
            ],
        )

    def test_tie_breaks_toward_greater_overlap(self):
        _punch(self.karyawan, self.home, self.focus, '07:00', '08:00')
        _punch(self.karyawan, self.home, self.focus, '09:00', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.total_menit_telat, 60)
        self.assertIn('absen masuk 09:00', _notes(rekap, self.focus)[0])

    def test_one_appearance_covers_multiple_shift_rows(self):
        _shift(self.home, self.workday, '13:00', '17:00')
        _punch(self.karyawan, self.home, self.focus, '13:00', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.hari_telat, 0)
        self.assertEqual(rekap.hari_alpa, len(self.scheduled) - 1)
        self.assertEqual(_notes(rekap, self.focus), [])

    def test_alpa_lists_every_home_shift(self):
        _shift(self.home, self.workday, '13:00', '21:00')
        rekap = self._rekap()
        self.assertEqual(
            _notes(rekap, self.focus),
            ['Tidak hadir (alpa). Jadwal shift 08:00–17:00, 13:00–21:00.'],
        )

    def test_overnight_shift_early_leave_and_lembur(self):
        Shift.objects.filter(lokasi_kerja=self.home).delete()
        _shift(self.home, self.workday, '22:00', '06:00')
        _punch(self.karyawan, self.other, self.focus, '22:00', '05:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.hari_keluar_cepat, 1)
        self.assertEqual(
            _notes(rekap, self.focus),
            ['Pulang lebih cepat 60 menit. Jadwal keluar 06:00, absen keluar 05:00.'],
        )

        Absensi.objects.filter(karyawan=self.karyawan).delete()
        _punch(self.karyawan, self.other, self.focus, '22:00', '07:00')
        PermohonanLembur.objects.create(
            karyawan=self.karyawan,
            tanggal=self.focus,
            status=StatusPermohonanLembur.APPROVED,
        )
        rekap = self._rekap()
        self.assertEqual(rekap.hari_keluar_cepat, 0)
        self.assertEqual(rekap.total_menit_lembur, 60)

    def test_reprocess_replaces_summary_and_notes(self):
        first = self._rekap()
        self.assertEqual(first.hari_alpa, len(self.scheduled))
        self.assertTrue(_notes(first, self.focus))

        _punch(self.karyawan, self.other, self.focus, '08:00', '17:00')
        second = self._rekap()
        self.assertEqual(
            RekapAbsensi.objects.filter(karyawan=self.karyawan, month=MONTH).count(),
            1,
        )
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.hari_hadir, 1)
        self.assertEqual(second.hari_alpa, len(self.scheduled) - 1)
        self.assertEqual(_notes(second, self.focus), [])

    def test_missing_lokasi_kerja(self):
        self.karyawan.lokasi_kerja = None
        self.karyawan.save(update_fields=['lokasi_kerja'])
        _punch(self.karyawan, self.other, self.focus, '08:00', '17:00')
        rekap = self._rekap()
        self.assertEqual(rekap.hari_hadir, 0)
        self.assertEqual(rekap.hari_alpa, 0)
        self.assertEqual(
            [row.pesan for row in rekap.catatan.all()],
            [
                'Karyawan tidak punya lokasi kerja, sehingga jadwal shift tidak bisa ditentukan.'
            ],
        )
        self.assertIsNone(rekap.catatan.get().tanggal)


class ProsesAbsensiApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.home = Lokasi.objects.create(id='81', nama='Toko 81')
        self.karyawan = _karyawan('1000001', 'Budi', self.home)
        _shift(self.home, 1, '08:00', '17:00')

    def test_proses_and_rekap_round_trip(self):
        created = self.client.post('/api/absensi/proses/', {'bulan': '2026-09'}, format='json')
        self.assertEqual(created.status_code, 200)
        self.assertEqual(len(created.data), 1)
        self.assertEqual(created.data[0]['karyawan_id'], '1000001')
        self.assertEqual(created.data[0]['month'], '2026-09-01')
        self.assertGreater(created.data[0]['hari_alpa'], 0)
        self.assertTrue(created.data[0]['catatan'])

        listed = self.client.get('/api/absensi/rekap/', {'bulan': '2026-09'})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]['id'], created.data[0]['id'])
        self.assertEqual(listed.data[0]['hari_alpa'], created.data[0]['hari_alpa'])

    def test_invalid_bulan_rejected(self):
        response = self.client.post('/api/absensi/proses/', {'bulan': 'September'}, format='json')
        self.assertEqual(response.status_code, 400)
        missing = self.client.get('/api/absensi/rekap/')
        self.assertEqual(missing.status_code, 400)


class ProsesKehadiranTests(TestCase):
    def setUp(self):
        self.home = Lokasi.objects.create(id='81', nama='Toko 81')
        self.other = Lokasi.objects.create(id='99', nama='Toko 99')
        self.karyawan = _karyawan('1000001', 'Budi', self.home)
        self.workday = 1
        self.scheduled = _days_in_month(self.workday)
        self.focus = self.scheduled[0]
        self.today = date(2026, 10, 1)
        _shift(self.home, self.workday, '08:00', '17:00')
        _shift(self.other, self.workday, '09:00', '18:00')

    def _on(self, day):
        return list(
            Kehadiran.objects.filter(karyawan=self.karyawan, tanggal=day).order_by('id')
        )

    def test_cross_location_lateness_uses_home_shift(self):
        _punch(self.karyawan, self.other, self.focus, '08:30', '17:00')
        counts = proses_kehadiran(self.today)
        row = self._on(self.focus)[0]
        self.assertEqual(counts['hadir'], 1)
        self.assertEqual(counts['alpa'], len(self.scheduled) - 1)
        self.assertEqual(row.status, StatusKehadiran.HADIR)
        self.assertEqual(row.menit_telat, 30)
        self.assertEqual(row.cepat_keluar, 0)
        self.assertEqual(row.lembur, 0)
        self.assertEqual(row.shift.lokasi_kerja_id, '81')
        self.assertEqual(row.absensi.lokasi_id, '99')
        rekap = RekapAbsensi.objects.get(karyawan=self.karyawan, month=date(2026, 9, 1))
        self.assertEqual(rekap.hari_hadir, 1)
        self.assertEqual(rekap.total_menit_telat, 30)

    def test_one_kehadiran_per_shift_day_uses_best_punch(self):
        _punch(self.karyawan, self.other, self.focus, '07:00', '08:00')
        kept = _punch(self.karyawan, self.other, self.focus, '08:05', '17:00')
        proses_kehadiran(self.today)
        rows = self._on(self.focus)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, StatusKehadiran.HADIR)
        self.assertEqual(rows[0].absensi_id, kept.pk)
        self.assertEqual(rows[0].menit_telat, 5)
        self.assertEqual(
            Kehadiran.objects.filter(karyawan=self.karyawan).count(),
            len(self.scheduled),
        )

    def test_alpa_when_shift_and_no_punch(self):
        counts = proses_kehadiran(self.today)
        self.assertEqual(counts['alpa'], len(self.scheduled))
        row = self._on(self.focus)[0]
        self.assertEqual(row.status, StatusKehadiran.ALPA)
        self.assertIsNone(row.absensi_id)
        self.assertEqual(row.shift.lokasi_kerja_id, '81')

    def test_full_day_cuti_and_liburan(self):
        _cuti(self.karyawan, TipeCuti.SAKIT, self.focus)
        holiday = self.scheduled[1]
        Liburan.objects.create(nama='Libur Toko', tanggal=holiday)
        counts = proses_kehadiran(self.today)
        row = self._on(self.focus)[0]
        self.assertEqual(row.status, StatusKehadiran.CUTI)
        self.assertIsNotNone(row.cuti_id)
        self.assertIsNone(row.absensi_id)
        self.assertEqual(self._on(holiday), [])
        self.assertEqual(counts['cuti'], 1)
        self.assertEqual(counts['alpa'], len(self.scheduled) - 2)

    def test_izin_telat_and_pulang_cepat_zero_minutes(self):
        _punch(self.karyawan, self.home, self.focus, '08:20', '16:40')
        _cuti(self.karyawan, TipeCuti.IZIN_TELAT, self.focus)
        _cuti(self.karyawan, TipeCuti.IZIN_PULANG_CEPAT, self.focus)
        proses_kehadiran(self.today)
        row = self._on(self.focus)[0]
        self.assertEqual(row.status, StatusKehadiran.HADIR)
        self.assertIsNotNone(row.absensi_id)
        self.assertEqual(row.menit_telat, 0)
        self.assertEqual(row.cepat_keluar, 0)
        self.assertIsNotNone(row.cuti_id)

    def test_lembur_only_when_already_approved(self):
        _punch(self.karyawan, self.home, self.focus, '08:00', '17:45')
        pending = PermohonanLembur.objects.create(
            karyawan=self.karyawan,
            tanggal=self.focus,
            status=StatusPermohonanLembur.MENUNGGU_HRD,
        )
        proses_kehadiran(self.today)
        row = self._on(self.focus)[0]
        self.assertEqual(row.lembur, 0)
        self.assertIsNone(row.permohonan_lembur_id)

        pending.status = StatusPermohonanLembur.APPROVED
        pending.save(update_fields=['status'])
        again = proses_kehadiran(self.today)
        row.refresh_from_db()
        self.assertEqual(again['hadir'], 0)
        self.assertEqual(row.lembur, 45)
        self.assertEqual(row.permohonan_lembur_id, pending.pk)

    def test_skip_already_processed(self):
        _punch(self.karyawan, self.home, self.focus, '08:00', '17:00')
        first = proses_kehadiran(self.today)
        second = proses_kehadiran(self.today)
        self.assertEqual(first['hadir'], 1)
        self.assertEqual(second['hadir'], 0)
        self.assertEqual(second['alpa'], 0)
        self.assertEqual(
            Kehadiran.objects.filter(
                karyawan=self.karyawan, status=StatusKehadiran.HADIR
            ).count(),
            1,
        )

    def test_does_not_process_today(self):
        today = self.scheduled[1]
        _punch(self.karyawan, self.home, today, '08:00', '17:00')
        proses_kehadiran(today)
        self.assertFalse(Kehadiran.objects.filter(tanggal=today).exists())
        self.assertEqual(self._on(self.focus)[0].status, StatusKehadiran.ALPA)

    def test_later_punch_replaces_alpa(self):
        proses_kehadiran(self.today)
        self.assertEqual(self._on(self.focus)[0].status, StatusKehadiran.ALPA)
        _punch(self.karyawan, self.other, self.focus, '08:00', '17:00')
        proses_kehadiran(self.today)
        rows = self._on(self.focus)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, StatusKehadiran.HADIR)
        self.assertIsNotNone(rows[0].absensi_id)
        self.assertIsNone(rows[0].cuti_id)
        self.assertEqual(rows[0].menit_telat, 0)

    def test_cuti_without_punch_has_no_absensi(self):
        cuti = _cuti(self.karyawan, TipeCuti.TAHUNAN, self.focus)
        _punch(self.karyawan, self.home, self.scheduled[1], '08:00', '17:00')
        proses_kehadiran(self.today)
        leave = self._on(self.focus)[0]
        worked = self._on(self.scheduled[1])[0]
        self.assertEqual(leave.status, StatusKehadiran.CUTI)
        self.assertIsNone(leave.absensi_id)
        self.assertEqual(leave.cuti_id, cuti.pk)
        self.assertEqual(worked.status, StatusKehadiran.HADIR)
        self.assertIsNotNone(worked.absensi_id)
        self.assertIsNone(worked.cuti_id)


class ProsesKehadiranApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.home = Lokasi.objects.create(id='81', nama='Toko 81')
        self.karyawan = _karyawan('1000001', 'Budi', self.home)
        _shift(self.home, 1, '08:00', '17:00')
        user = User.objects.create_user(username='budi', password='x')
        self.karyawan.user = user
        self.karyawan.save(update_fields=['user'])
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_manual_proses_and_portal_list(self):
        focus = _days_in_month(1)[0]
        _punch(self.karyawan, self.home, focus, '08:10', '17:00')
        created = self.client.post('/api/absensi/proses-kehadiran/')
        self.assertEqual(created.status_code, 200)
        self.assertGreaterEqual(created.data['hadir'], 1)
        self.assertIn('alpa', created.data)

        listed = self.client.get('/api/portal/kehadiran/', {'bulan': '2026-09'})
        self.assertEqual(listed.status_code, 200)
        match = next(row for row in listed.data if row['tanggal'] == focus.isoformat())
        self.assertEqual(match['status'], 'HADIR')
        self.assertEqual(match['status_display'], 'Hadir')
        self.assertEqual(match['menit_telat'], 10)
        self.assertEqual(match['shift_jam_masuk'], '08:00:00')

    def test_hapus_kehadiran_for_month(self):
        focus = _days_in_month(1)[0]
        _punch(self.karyawan, self.home, focus, '08:00', '17:00')
        self.client.post('/api/absensi/proses-kehadiran/')
        self.assertGreater(
            Kehadiran.objects.filter(tanggal__year=2026, tanggal__month=9).count(),
            0,
        )

        removed = self.client.post(
            '/api/absensi/hapus-kehadiran/',
            {'bulan': '2026-09'},
            format='json',
        )
        self.assertEqual(removed.status_code, 200)
        self.assertGreater(removed.data['deleted'], 0)
        self.assertEqual(removed.data['bulan'], '2026-09')
        self.assertFalse(
            Kehadiran.objects.filter(tanggal__year=2026, tanggal__month=9).exists()
        )
        self.assertTrue(Absensi.objects.filter(karyawan=self.karyawan).exists())

        missing = self.client.post(
            '/api/absensi/hapus-kehadiran/',
            {'bulan': 'September'},
            format='json',
        )
        self.assertEqual(missing.status_code, 400)
