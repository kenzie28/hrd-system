from django.db import models


class TipeKoreksi(models.TextChoices):
    ADMIN = 'ADMIN', 'Koreksi Admin'
    ABSENSI = 'ABSENSI', 'Koreksi Absensi'


class Koreksi(models.Model):
    karyawan = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='koreksi',
    )
    tipe = models.CharField(max_length=16, choices=TipeKoreksi.choices)
    nominal = models.BigIntegerField()
    tanggal = models.DateField()

    class Meta:
        verbose_name_plural = 'Koreksi'
        ordering = ['-tanggal', 'karyawan__nama', 'id']

    def __str__(self):
        return f'{self.karyawan} {self.get_tipe_display()} {self.tanggal:%Y-%m}'
