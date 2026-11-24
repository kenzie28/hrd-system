from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class JenisKelamin(models.TextChoices):
    PEREMPUAN = 'Perempuan', 'Perempuan'
    LAKI_LAKI = 'Laki-Laki', 'Laki-Laki'


class StatusKTk(models.TextChoices):
    TK = 'TK', 'TK'
    TK1 = 'TK1', 'TK1'
    TK2 = 'TK2', 'TK2'
    TK3 = 'TK3', 'TK3'
    K0 = 'K0', 'K0'
    K1 = 'K1', 'K1'
    K2 = 'K2', 'K2'
    K3 = 'K3', 'K3'


class Karyawan(models.Model):
    karyawan_id = models.CharField(max_length=7, primary_key=True)
    nama = models.CharField(max_length=128)
    jenis_kelamin = models.CharField(
        max_length=9, choices=JenisKelamin.choices, blank=True, default=''
    )
    tanggal_lahir = models.DateField(null=True, blank=True)
    tanggal_awal = models.DateField(null=True, blank=True)
    tanggal_kontrak_awal = models.DateField(null=True, blank=True)
    tanggal_kontrak_akhir = models.DateField(null=True, blank=True)
    status_kontrak = models.CharField(max_length=2, blank=True, default='')
    tanggal_keluar = models.DateField(null=True, blank=True)
    lokasi_kerja = models.ForeignKey(
        'lokasi.Lokasi',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karyawan',
    )
    jabatan = models.CharField(max_length=128, blank=True, default='')
    percobaan_jabatan = models.BooleanField(default=False)
    wilayah = models.CharField(max_length=3, blank=True, default='')
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(9)]
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
    base_gaji = models.PositiveBigIntegerField(default=0)
    gaji_bulanan = models.PositiveBigIntegerField(default=0)
    status_k_tk = models.CharField(
        max_length=3, choices=StatusKTk.choices, blank=True, default=''
    )
    lembur_dibayar = models.BooleanField(default=False)
    akumulasi_lembur = models.PositiveIntegerField(default=0)
    npwp = models.CharField(max_length=20, blank=True, default='')
    kpj = models.CharField(max_length=16, blank=True, default='')
    tanggal_kpj = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Karyawan'

    def __str__(self):
        return self.nama

    @property
    def active(self):
        if self.tanggal_keluar is None:
            return True
        return self.tanggal_keluar >= timezone.localdate()

    @property
    def lama_kerja(self):
        if self.tanggal_awal is None:
            return None
        today = timezone.localdate()
        end = today
        if self.tanggal_keluar is not None and self.tanggal_keluar < today:
            end = self.tanggal_keluar
        return _completed_years(self.tanggal_awal, end)

    @property
    def umur(self):
        if self.tanggal_lahir is None:
            return None
        return _completed_years(self.tanggal_lahir, timezone.localdate())


def _completed_years(start, end):
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return max(years, 0)
