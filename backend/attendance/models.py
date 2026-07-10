from datetime import datetime

from django.db import models


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
        'cuti.Cuti',
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
