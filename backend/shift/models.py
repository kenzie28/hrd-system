from django.db import models


class HariKerja(models.TextChoices):
    SENIN = 'SENIN', 'Senin'
    SELASA = 'SELASA', 'Selasa'
    RABU = 'RABU', 'Rabu'
    KAMIS = 'KAMIS', 'Kamis'
    JUMAT = 'JUMAT', 'Jumat'
    SABTU = 'SABTU', 'Sabtu'
    MINGGU = 'MINGGU', 'Minggu'


class Shift(models.Model):
    lokasi_kerja = models.ForeignKey(
        'lokasi.Lokasi', on_delete=models.CASCADE, related_name='shifts'
    )
    hari = models.CharField(max_length=8, choices=HariKerja.choices)
    jam_masuk = models.TimeField()
    jam_keluar = models.TimeField()

    class Meta:
        verbose_name_plural = 'Shift'
        ordering = ['lokasi_kerja', 'hari', 'jam_masuk']

    def __str__(self):
        return (
            f'{self.lokasi_kerja} - {self.get_hari_display()} '
            f'({self.jam_masuk:%H:%M}-{self.jam_keluar:%H:%M})'
        )
