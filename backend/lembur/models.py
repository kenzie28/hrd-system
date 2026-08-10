from django.db import models


class StatusPermohonanLembur(models.TextChoices):
    MENUNGGU_SUPERVISOR = 'MENUNGGU_SUPERVISOR', 'Menunggu Izin Supervisor'
    MENUNGGU_HRD = 'MENUNGGU_HRD', 'Menunggu Izin HRD'
    DITOLAK = 'DITOLAK', 'Request Ditolak'
    DIBATALKAN = 'DIBATALKAN', 'Dibatalkan'
    APPROVED = 'APPROVED', 'Approved'


# States from which the workflow can still progress or be cancelled.
ACTIVE_STATUSES = {
    StatusPermohonanLembur.MENUNGGU_SUPERVISOR,
    StatusPermohonanLembur.MENUNGGU_HRD,
}


class PermohonanLembur(models.Model):
    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.PROTECT, related_name='permohonan_lembur'
    )
    alasan = models.TextField(blank=True)
    tanggal = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=StatusPermohonanLembur.choices,
        default=StatusPermohonanLembur.MENUNGGU_SUPERVISOR,
    )
    supervisor = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='lembur_disupervisi',
        null=True,
        blank=True,
    )
    hrd_approver = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='lembur_diapprove_hrd',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = 'Permohonan Lembur'
        ordering = ['-tanggal']

    def __str__(self):
        return f'{self.karyawan} - Lembur ({self.tanggal})'
