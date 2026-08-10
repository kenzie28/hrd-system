from django.db import models


class Liburan(models.Model):
    nama = models.CharField(max_length=64)
    tanggal = models.DateField()

    class Meta:
        verbose_name_plural = 'Liburan'
        ordering = ['tanggal']

    def __str__(self):
        return f'{self.nama} ({self.tanggal})'
