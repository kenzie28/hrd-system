from datetime import datetime

from django.db import models


class TipeCuti(models.TextChoices):
    IZIN = 'IZIN', 'Izin'
    IZIN_TELAT = 'IZIN_TELAT', 'Izin Telat'
    IZIN_PULANG_CEPAT = 'IZIN_PULANG_CEPAT', 'Izin Pulang Cepat'
    TAHUNAN = 'TAHUNAN', 'Tahunan'
    SAKIT = 'SAKIT', 'Sakit'
    DUKA_CITA = 'DUKA_CITA', 'Duka Cita'
    MELAHIRKAN = 'MELAHIRKAN', 'Melahirkan'
    ISTRI_MELAHIRKAN = 'ISTRI_MELAHIRKAN', 'Istri Melahirkan'
    MENIKAH = 'MENIKAH', 'Menikah'
    ANAK_MENIKAH = 'ANAK_MENIKAH', 'Anak Menikah'
    KHITANAN_ANAK = 'KHITANAN_ANAK', 'Khitanan Anak'
    PEMBAPTISAN_ANAK = 'PEMBAPTISAN_ANAK', 'Pembaptisan Anak'


class StatusPermohonanCuti(models.TextChoices):
    MENUNGGU_SUPERVISOR = 'MENUNGGU_SUPERVISOR', 'Menunggu Izin Supervisor'
    MENUNGGU_HRD = 'MENUNGGU_HRD', 'Menunggu Izin HRD'
    DITOLAK = 'DITOLAK', 'Request Ditolak'
    DIBATALKAN = 'DIBATALKAN', 'Dibatalkan'
    APPROVED = 'APPROVED', 'Approved'


class StatusRekapKehadiran(models.TextChoices):
    HADIR = 'HADIR', 'Hadir'
    TERLAMBAT = 'TERLAMBAT', 'Terlambat'
    PULANG_CEPAT = 'PULANG_CEPAT', 'Pulang Cepat'
    IZIN = 'IZIN', 'Izin'
    SAKIT = 'SAKIT', 'Sakit'
    CUTI = 'CUTI', 'Cuti'
    ALPA = 'ALPA', 'Alpa'
    LIBUR = 'LIBUR', 'Libur'


class Shift(models.Model):
    jam_masuk = models.TimeField()
    jam_keluar = models.TimeField()

    class Meta:
        verbose_name_plural = 'Shift'
        ordering = ['jam_masuk']

    def __str__(self):
        return f'{self.jam_masuk:%H:%M} - {self.jam_keluar:%H:%M}'


class Jadwal(models.Model):
    karyawan = models.ForeignKey(
        'core.Karyawan', on_delete=models.CASCADE, related_name='jadwal'
    )
    shift = models.ForeignKey(
        Shift, on_delete=models.CASCADE, related_name='jadwal')
    tanggal = models.DateField()

    class Meta:
        verbose_name_plural = 'Jadwal'
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'tanggal'], name='unique_jadwal_karyawan_tanggal'
            )
        ]
        ordering = ['tanggal', 'karyawan__nama']

    def __str__(self):
        return f'{self.karyawan} @ {self.tanggal} ({self.shift})'


class Absensi(models.Model):
    karyawan = models.ForeignKey(
        'core.Karyawan', on_delete=models.CASCADE, related_name='absensi'
    )
    lokasi = models.ForeignKey(
        'core.Lokasi', on_delete=models.CASCADE, related_name='absensi'
    )
    tanggal = models.DateField()
    jam_masuk = models.TimeField()
    durasi = models.DurationField()

    class Meta:
        verbose_name_plural = 'Absensi'
        ordering = ['-tanggal', 'karyawan__nama']

    @property
    def jam_keluar(self):
        keluar = datetime.combine(self.tanggal, self.jam_masuk) + self.durasi
        return keluar.time()

    @property
    def keluar_hari_offset(self) -> int:
        """Calendar days after tanggal when jam keluar occurs (0 = same day)."""
        keluar = datetime.combine(self.tanggal, self.jam_masuk) + self.durasi
        return (keluar.date() - self.tanggal).days

    def __str__(self):
        return f'{self.karyawan} @ {self.tanggal} {self.jam_masuk:%H:%M}'


class PermohonanCuti(models.Model):
    # Workflow and Range Data
    karyawan = models.ForeignKey(
        'core.Karyawan', on_delete=models.PROTECT, related_name='permohonan_cuti'
    )
    tipe = models.CharField(max_length=32, choices=TipeCuti.choices)
    alasan = models.TextField(blank=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    status = models.CharField(
        max_length=32, choices=StatusPermohonanCuti.choices, default=StatusPermohonanCuti.MENUNGGU_SUPERVISOR
    )
    supervisor = models.ForeignKey(
        'core.Karyawan',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cuti_disupervisi',
    )

    class Meta:
        verbose_name_plural = 'Permohonan Cuti'
        ordering = ['-tanggal_mulai']

    def __str__(self):
        return f'{self.karyawan} - {self.get_tipe_display()} ({self.tanggal_mulai} s/d {self.tanggal_selesai})'


class Cuti(models.Model):
    # Factual Daily Ledger Data
    permohonan = models.ForeignKey(
        PermohonanCuti, on_delete=models.CASCADE, related_name='hari_cuti'
    )
    tanggal = models.DateField()

    class Meta:
        verbose_name_plural = 'Cuti'
        ordering = ['-tanggal']

    @property
    def karyawan(self):
        return self.permohonan.karyawan

    @property
    def tipe(self):
        return self.permohonan.tipe

    def __str__(self):
        return f'{self.karyawan} - {self.permohonan.get_tipe_display()} @ {self.tanggal}'


class RekapKehadiran(models.Model):
    jadwal = models.OneToOneField(
        Jadwal, on_delete=models.CASCADE, related_name='rekap'
    )
    absensi = models.ForeignKey(
        Absensi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rekap',
    )
    cuti = models.ForeignKey(
        Cuti,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rekap',
    )
    status = models.CharField(
        max_length=16, choices=StatusRekapKehadiran.choices)

    class Meta:
        verbose_name_plural = 'Rekap Kehadiran'
        ordering = ['jadwal__tanggal', 'jadwal__karyawan__nama']

    @property
    def karyawan(self):
        return self.jadwal.karyawan

    def __str__(self):
        return f'{self.jadwal} -> {self.get_status_display()}'


class Liburan(models.Model):
    nama = models.CharField(max_length=64)
    tanggal = models.DateField()

    class Meta:
        verbose_name_plural = 'Liburan'
        ordering = ['tanggal']

    def __str__(self):
        return f'{self.nama} ({self.tanggal})'
