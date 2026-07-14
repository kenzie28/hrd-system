from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Karyawan(models.Model):
    karyawan_id = models.CharField(max_length=7, unique=True)
    nama = models.CharField(max_length=128)
    lokasi_kerja = models.ForeignKey(
        'core.Lokasi',
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
    default_shift = models.ForeignKey(
        'attendance.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karyawan_default',
    )
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karyawan',
    )
    must_change_password = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Karyawan'

    def __str__(self):
        return self.nama
