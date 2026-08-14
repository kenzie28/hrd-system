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
