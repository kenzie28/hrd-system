from datetime import datetime

from django.db import models


class Absensi(models.Model):
    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='absensi'
    )
    lokasi = models.ForeignKey(
        'lokasi.Lokasi', on_delete=models.CASCADE, related_name='absensi'
    )
    tanggal = models.DateField()
    jam_masuk = models.TimeField()
    durasi = models.DurationField()

    class Meta:
        verbose_name_plural = 'Absensi'
        ordering = ['-tanggal', 'karyawan__nama']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'lokasi', 'tanggal', 'jam_masuk', 'durasi'],
                name='absensi_unique_exact_entry',
            ),
        ]

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


class RekapAbsensi(models.Model):
    """Monthly attendance summary for one employee, produced by Proses Absensi."""

    month = models.DateField(help_text='First day of the processed month.')
    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='rekap_absensi'
    )
    hari_hadir = models.PositiveIntegerField(default=0)
    hari_telat = models.PositiveIntegerField(default=0)
    hari_alpa = models.PositiveIntegerField(default=0)
    hari_keluar_cepat = models.PositiveIntegerField(default=0)
    total_menit_telat = models.PositiveIntegerField(default=0)
    total_menit_lembur = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Rekap Absensi'
        ordering = ['-month', 'karyawan__nama']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'month'],
                name='rekap_absensi_unique_karyawan_month',
            ),
        ]

    def __str__(self):
        return f'{self.karyawan} — {self.month:%Y-%m}'


class CatatanRekapAbsensi(models.Model):
    """One Indonesian note about a day (or the month) in a RekapAbsensi."""

    rekap = models.ForeignKey(
        RekapAbsensi, on_delete=models.CASCADE, related_name='catatan'
    )
    tanggal = models.DateField(null=True, blank=True)
    pesan = models.TextField()

    class Meta:
        verbose_name_plural = 'Catatan Rekap Absensi'
        ordering = ['tanggal', 'id']

    def __str__(self):
        when = self.tanggal.isoformat() if self.tanggal else 'bulan'
        return f'{when}: {self.pesan}'
