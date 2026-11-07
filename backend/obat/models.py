from django.db import models


class TunjanganObat(models.Model):
    karyawan = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='tunjangan_obat',
    )
    nominal = models.PositiveBigIntegerField()
    bulan = models.DateField(
        help_text='First day of the month this allowance applies to.',
    )

    class Meta:
        verbose_name = 'Tunjangan Obat'
        verbose_name_plural = 'Tunjangan Obat'
        ordering = ['-bulan', 'karyawan__nama', 'id']

    def __str__(self):
        return f'{self.karyawan} Tunjangan Obat {self.bulan:%Y-%m}'
