import calendar
import random
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from attendance.models import (
    Absensi,
    Jadwal,
    Liburan,
    Shift,
)
from core.models import Lokasi
from karyawan.models import Karyawan
from cuti.models import (
    Cuti,
    PermohonanCuti,
    StatusPermohonanCuti,
    TipeCuti,
)


class Command(BaseCommand):
    help = 'Seed demo data (lokasi, karyawan, shifts, liburan, jadwal, absensi, cuti) for the current month.'

    def handle(self, *args, **options):
        rng = random.Random(42)
        today = date.today()
        first_day = today.replace(day=1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        last_day = today.replace(day=days_in_month)

        pagi, _ = Shift.objects.get_or_create(jam_masuk=time(8, 0), jam_keluar=time(16, 0))
        siang, _ = Shift.objects.get_or_create(jam_masuk=time(9, 0), jam_keluar=time(17, 0))
        sore, _ = Shift.objects.get_or_create(jam_masuk=time(14, 0), jam_keluar=time(22, 0))

        kantor, _ = Lokasi.objects.get_or_create(id='01', defaults={'nama': 'Kantor Pusat'})
        cabang, _ = Lokasi.objects.get_or_create(id='02', defaults={'nama': 'Cabang Bandung'})
        lokasi_list = [kantor, cabang]

        # (nama, shift, level). The first employee is a level-5 supervisor so
        # the level 1-4 requesters below may pick them (see cuti.policy).
        nama_karyawan = [
            ('Andi Wijaya', pagi, 5),
            ('Budi Santoso', pagi, 1),
            ('Citra Lestari', siang, 2),
            ('Dewi Anggraini', siang, 3),
            ('Eko Prasetyo', sore, 4),
        ]
        karyawan_list = []
        for i, (nama, shift, level) in enumerate(nama_karyawan, start=1):
            k, created = Karyawan.objects.get_or_create(
                karyawan_id=str(i).zfill(7),
                defaults={'nama': nama, 'default_shift': shift, 'level': level},
            )
            if not created and k.level != level:
                k.level = level
                k.save(update_fields=['level'])
            karyawan_list.append((k, shift))

        # HRD approver used by the admin-frontend allowlist (karyawan.access).
        Karyawan.objects.update_or_create(
            karyawan_id='9610003',
            defaults={'nama': 'RINI KURNIASIH', 'level': 8},
        )

        supervisor = karyawan_list[0][0]

        Liburan.objects.get_or_create(
            nama='Hari Libur Nasional', tanggal=first_day + timedelta(days=16)
        )

        # Jadwal on weekdays for the whole month
        for k, shift in karyawan_list:
            for day_offset in range(days_in_month):
                tanggal = first_day + timedelta(days=day_offset)
                if tanggal.weekday() >= 5:
                    continue
                Jadwal.objects.get_or_create(
                    karyawan=k, tanggal=tanggal, defaults={'shift': shift}
                )

        # PermohonanCuti: approved requests get daily Cuti ledger rows; one still pending
        cuti_specs = [
            (karyawan_list[1][0], TipeCuti.SAKIT, 7, 8, StatusPermohonanCuti.APPROVED),
            (karyawan_list[2][0], TipeCuti.TAHUNAN, 13, 15, StatusPermohonanCuti.APPROVED),
            (karyawan_list[3][0], TipeCuti.IZIN_OFF, 9, 9, StatusPermohonanCuti.APPROVED),
            (karyawan_list[4][0], TipeCuti.MENIKAH, 20, 22, StatusPermohonanCuti.MENUNGGU_HRD),
        ]
        cuti_ranges = {}
        for k, tipe, start_off, end_off, cuti_status in cuti_specs:
            mulai = first_day + timedelta(days=start_off)
            selesai = first_day + timedelta(days=end_off)
            permohonan, _ = PermohonanCuti.objects.get_or_create(
                karyawan=k,
                tipe=tipe,
                tanggal_mulai=mulai,
                tanggal_selesai=selesai,
                defaults={'status': cuti_status, 'supervisor': supervisor},
            )
            if cuti_status == StatusPermohonanCuti.APPROVED:
                cuti_ranges.setdefault(k.id, []).append((mulai, selesai))
                for day_offset in range((selesai - mulai).days + 1):
                    Cuti.objects.get_or_create(
                        permohonan=permohonan,
                        tanggal=mulai + timedelta(days=day_offset),
                    )

        # Absensi for scheduled weekdays up to today (skip approved cuti days, ~10% alpa)
        created_absensi = 0
        for k, shift in karyawan_list:
            for day_offset in range(days_in_month):
                tanggal = first_day + timedelta(days=day_offset)
                if tanggal > today or tanggal.weekday() >= 5:
                    continue
                if any(m <= tanggal <= s for m, s in cuti_ranges.get(k.id, [])):
                    continue
                if rng.random() < 0.1:
                    continue  # alpa

                roll = rng.random()
                if roll < 0.15:  # terlambat
                    masuk_offset = rng.randint(10, 60)
                    durasi_hours = 8
                elif roll < 0.30:  # pulang cepat
                    masuk_offset = -rng.randint(0, 10)
                    durasi_hours = 6
                else:  # hadir
                    masuk_offset = -rng.randint(0, 15)
                    durasi_hours = 8 + rng.randint(0, 1)

                masuk_dt = (
                    timedelta(hours=shift.jam_masuk.hour, minutes=shift.jam_masuk.minute)
                    + timedelta(minutes=masuk_offset)
                )
                jam_masuk = time(
                    int(masuk_dt.total_seconds() // 3600) % 24,
                    int(masuk_dt.total_seconds() % 3600 // 60),
                )
                _, created = Absensi.objects.get_or_create(
                    karyawan=k,
                    tanggal=tanggal,
                    defaults={
                        'lokasi': rng.choice(lokasi_list),
                        'jam_masuk': jam_masuk,
                        'durasi': timedelta(hours=durasi_hours, minutes=rng.randint(0, 30)),
                    },
                )
                created_absensi += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded: {Karyawan.objects.count()} karyawan, {Shift.objects.count()} shifts, '
            f'{Jadwal.objects.count()} jadwal, {Absensi.objects.count()} absensi '
            f'({created_absensi} new), {PermohonanCuti.objects.count()} permohonan cuti '
            f'({Cuti.objects.count()} hari cuti), {Liburan.objects.count()} liburan. '
            f'Range: {first_day} .. {last_day}'
        ))
