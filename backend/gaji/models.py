from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Gaji(models.Model):
    """One employee's payroll breakdown for a single month.

    Process Gaji does not write this row yet. The fields are the intended
    snapshot of that month's attendance and wage components.
    """

    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.PROTECT, related_name='gaji'
    )
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
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

    base_gaji = models.IntegerField(default=0)
    gaji_bulanan = models.IntegerField(default=0)

    jam_lembur = models.IntegerField(default=0)
    hari_lembur = models.IntegerField(default=0)

    tunjangan_obat = models.PositiveIntegerField(default=0)
    tunjangan_dinas = models.PositiveIntegerField(default=0)

    pot_bpjs_jht = models.IntegerField(default=0)
    pot_bpjs_jp = models.IntegerField(default=0)
    pot_bpjs_kesehatan = models.IntegerField(default=0)
    pot_pph21 = models.IntegerField(default=0)
    pot_alpa = models.IntegerField(default=0)

    perusahan_bpjs_jht = models.IntegerField(default=0)
    perusahan_bpjs_jp = models.IntegerField(default=0)
    perusahan_bpjs_kesehatan = models.IntegerField(default=0)

    koreksi_absensi = models.IntegerField(default=0)
    koreksi_admin = models.IntegerField(default=0)

    total_gaji = models.PositiveIntegerField(
        default=0, help_text='Net.Transfer + Total Trf.U.Makan from the CSV.'
    )

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
