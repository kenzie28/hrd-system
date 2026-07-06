from django.db import models


class Lokasi(models.Model):
    id = models.CharField(max_length=2, primary_key=True)
    nama = models.CharField(max_length=128)

    class Meta:
        verbose_name_plural = 'Lokasi'

    def __str__(self):
        return self.nama


class Karyawan(models.Model):
    nama = models.CharField(max_length=128)
    default_shift = models.ForeignKey(
        'attendance.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karyawan_default',
    )

    class Meta:
        verbose_name_plural = 'Karyawan'

    def __str__(self):
        return self.nama
