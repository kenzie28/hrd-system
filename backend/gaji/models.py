from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from karyawan.models import StatusKTk

_TER_BY_STATUS_K_TK = {
    StatusKTk.TK: 'A',
    StatusKTk.TK1: 'A',
    StatusKTk.K0: 'A',
    StatusKTk.TK2: 'B',
    StatusKTk.TK3: 'B',
    StatusKTk.K1: 'B',
    StatusKTk.K2: 'B',
    StatusKTk.K3: 'C',
}


class Gaji(models.Model):
    """One employee's payroll breakdown for a single month.

    Proses Gaji writes this row as a snapshot of that month's attendance
    and wage components.
    """

    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.PROTECT, related_name='gaji'
    )
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(9)]
    )

    jabatan = models.CharField(max_length=128, blank=True, default='')
    periode = models.DateField(help_text='First day of the payroll month.')

    hari_hadir = models.PositiveIntegerField(default=0)
    hari_telat = models.PositiveIntegerField(default=0)
    total_menit_telat = models.PositiveIntegerField(default=0)
    hari_sakit = models.PositiveIntegerField(default=0)
    hari_cuti = models.PositiveIntegerField(default=0)
    hari_cuti_tambahan = models.PositiveIntegerField(default=0)
    hari_off = models.PositiveIntegerField(default=0)
    hari_alpa = models.PositiveIntegerField(default=0)
    hari_dinas = models.PositiveIntegerField(default=0)

    base_gaji_bpjs = models.IntegerField(default=0)

    jam_lembur = models.IntegerField(default=0)
    hari_lembur = models.IntegerField(default=0)
    jam_diakumulasi = models.PositiveIntegerField(
        default=0,
        help_text='Hours this row added to Karyawan.akumulasi_lembur. Zero when lembur is paid.',
    )

    pot_bpjs_jht = models.IntegerField(default=0)
    pot_bpjs_jp = models.IntegerField(default=0)
    pot_bpjs_kesehatan = models.IntegerField(default=0)

    @property
    def total_pot_bpjs(self):
        return self.pot_bpjs_jht + self.pot_bpjs_jp + self.pot_bpjs_kesehatan

    beban_bpjs_jht = models.IntegerField(default=0)
    beban_bpjs_jp = models.IntegerField(default=0)
    beban_bpjs_kesehatan = models.IntegerField(default=0)
    beban_bpjs_jkm = models.IntegerField(default=0)
    beban_bjps_jkk  = models.IntegerField(default=0)

    @property
    def total_beban_bpjs(self):
        return self.beban_bpjs_jht + self.beban_bpjs_jp + self.beban_bpjs_kesehatan + self.beban_bpjs_jkm + self.beban_bjps_jkk

    gaji_bulanan = models.IntegerField(default=0)

    @property
    def total_bpjs_benefit(self):
        return self.beban_bpjs_kesehatan + self.beban_bpjs_jkm + self.beban_bjps_jkk

    lembur_dibayar = models.BooleanField(default=False)
    gaji_lembur = models.IntegerField(default=0)

    tunjangan_obat = models.PositiveIntegerField(default=0)
    tunjangan_dinas = models.PositiveIntegerField(default=0)

    pot_alpa = models.IntegerField(default=0)

    koreksi_absensi = models.IntegerField(default=0)
    koreksi_admin = models.IntegerField(default=0)

    uang_terima_kasih = models.IntegerField(default=0)

    @property
    def net_penghasilan(self):
        return self.gaji_bulanan + self.total_bpjs_benefit + self.gaji_lembur + self.tunjangan_obat + self.tunjangan_dinas - self.pot_alpa + self.koreksi_absensi + self.koreksi_admin + self.uang_terima_kasih

    status_k_tk = models.CharField(
        max_length=3, choices=StatusKTk.choices, blank=True, default=''
    )

    @property
    def ter_status(self):
        return _TER_BY_STATUS_K_TK.get(self.status_k_tk, '')

    persentase_pph21 = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00')
    )
    pot_pph21 = models.IntegerField(default=0)

    total_gaji = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Gaji'
        ordering = ['-periode', 'karyawan__nama']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'periode'], name='unique_gaji_per_periode'
            ),
        ]

    def __str__(self):
        return f'{self.karyawan} - {self.periode:%Y-%m}'


class StatusProsesGaji(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class ProsesGajiJob(models.Model):
    """One background run of Proses Gaji for a single month."""

    periode = models.DateField(help_text='First day of the payroll month.')
    status = models.CharField(
        max_length=16,
        choices=StatusProsesGaji.choices,
        default=StatusProsesGaji.PENDING,
    )
    total = models.PositiveIntegerField(default=0)
    processed = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Proses Gaji'
        verbose_name_plural = 'Proses Gaji'

    def __str__(self):
        return f'{self.periode:%Y-%m} ({self.status})'
