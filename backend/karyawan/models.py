from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Karyawan(models.Model):
    karyawan_id = models.CharField(max_length=7, primary_key=True)
    nama = models.CharField(max_length=128)
    lokasi_kerja = models.ForeignKey(
        'lokasi.Lokasi',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karyawan',
    )
    jabatan = models.CharField(max_length=128, blank=True, default='')
    wilayah = models.CharField(max_length=3, blank=True, default='')
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karyawan',
    )
    must_change_password = models.BooleanField(default=True)
    cuti_tahunan = models.PositiveSmallIntegerField(
        default=12,
        help_text='Sisa jatah cuti tahunan (hari) yang masih bisa diambil.',
    )

    class Meta:
        verbose_name_plural = 'Karyawan'

    def __str__(self):
        return self.nama
