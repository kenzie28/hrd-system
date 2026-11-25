from django.db import models


class Dinas(models.Model):
    """One employee assigned to dinas on one calendar day.

    A row means the day is dinas. It is not an overtime request and does not
    add lembur minutes.
    """

    karyawan = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='dinas',
    )
    tanggal = models.DateField()

    class Meta:
        verbose_name = 'Dinas'
        verbose_name_plural = 'Dinas'
        ordering = ['-tanggal', 'karyawan__nama', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'tanggal'],
                name='dinas_unique_karyawan_tanggal',
            ),
        ]

    def __str__(self):
        return f'{self.karyawan} - Dinas ({self.tanggal})'
