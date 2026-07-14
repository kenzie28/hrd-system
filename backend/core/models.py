from django.db import models


class Lokasi(models.Model):
    id = models.CharField(max_length=2, primary_key=True)
    nama = models.CharField(max_length=128)

    class Meta:
        verbose_name_plural = 'Lokasi'

    def __str__(self):
        return self.nama
