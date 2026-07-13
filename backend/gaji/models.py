from decimal import ROUND_HALF_UP, Decimal

from django.db import models


def _round_rupiah(value) -> int:
    return int(Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


class GajiTemp(models.Model):
    """One employee's payroll breakdown for a single month, imported from the
    HRD payroll CSV export (see ``gaji-input.csv`` at the repo root)."""

    karyawan = models.ForeignKey(
        'core.Karyawan', on_delete=models.PROTECT, related_name='gaji_temp'
    )
    periode = models.DateField(help_text='First day of the payroll month.')

    # Attendance tally, from HADIR / SK/CU/CT.
    hadir = models.PositiveIntegerField(default=0)
    hari_sakit = models.PositiveIntegerField(default=0)
    hari_cuti = models.PositiveIntegerField(default=0)
    hari_cuti_tambahan = models.PositiveIntegerField(default=0)

    # Personal target incentive.
    freq_pencapaian_target = models.PositiveIntegerField(default=0)
    rate_target = models.PositiveIntegerField(default=0)

    # Non-target ("UMP+") pay for days not covered by the target incentive.
    rate_non_target = models.PositiveIntegerField(default=0)

    gaji_pokok = models.PositiveIntegerField(default=0)

    # Meal allowance.
    rate_uang_makan = models.PositiveIntegerField(default=35000)

    # Overtime ("Lembur", in 6-hour blocks) — kept as Decimal since the
    # source data has fractional block counts (e.g. 0.68, 15.72).
    freq_lembur_6_jam = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    rate_lembur_6_jam = models.PositiveIntegerField(default=0)

    # Holiday pay ("RY").
    freq_hari_raya = models.PositiveIntegerField(default=0)

    tunjangan_lama_kerja = models.PositiveIntegerField(default=0)
    tunjangan_obat = models.PositiveIntegerField(default=0)

    freq_alpa = models.PositiveIntegerField(default=0)

    # Deductions — stored as-is (already <= 0) from the CSV.
    pot_bpjs_jht = models.IntegerField(default=0)
    pot_bpjs_jp = models.IntegerField(default=0)
    pot_bpjs_kesehatan = models.IntegerField(default=0)
    pot_pph21 = models.IntegerField(default=0)
    pot_kehilangan = models.IntegerField(default=0)

    koreksi_absensi = models.IntegerField(default=0)

    total_gaji = models.PositiveIntegerField(
        default=0, help_text='Net.Transfer + Total Trf.U.Makan from the CSV.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Gaji Temp'
        ordering = ['-periode', 'karyawan__nama']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'periode'], name='unique_gaji_temp_per_periode'
            ),
        ]

    def __str__(self):
        return f'{self.karyawan} - {self.periode:%Y-%m}'

    @property
    def nominal_target(self) -> int:
        return self.rate_target * self.freq_pencapaian_target

    @property
    def freq_hari_non_target(self) -> int:
        return self.hadir - self.freq_pencapaian_target

    @property
    def nominal_non_target(self) -> int:
        return self.rate_non_target * self.freq_hari_non_target

    @property
    def nominal_uang_makan(self) -> int:
        return self.rate_uang_makan * self.hadir

    @property
    def rate_hari_raya(self) -> int:
        return _round_rupiah(Decimal(self.rate_lembur_6_jam) / 6 * 8)

    @property
    def nominal_lembur(self) -> int:
        return _round_rupiah(self.freq_lembur_6_jam * self.rate_lembur_6_jam)

    @property
    def nominal_hari_raya(self) -> int:
        return self.freq_hari_raya * self.rate_hari_raya

    @property
    def pengurang_alpa(self) -> int:
        if self.rate_non_target:
            return -self.freq_alpa * self.rate_non_target
        return _round_rupiah(Decimal(-self.freq_alpa) / 20 * self.gaji_pokok)
