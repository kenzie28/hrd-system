from django.db import models


class TipeCuti(models.TextChoices):
    IZIN_OFF = 'IZIN_OFF', 'Izin Off'
    IZIN_TELAT = 'IZIN_TELAT', 'Izin Telat'
    IZIN_PULANG_CEPAT = 'IZIN_PULANG_CEPAT', 'Izin Pulang Cepat'
    IZIN_LOKASI_BEDA = 'IZIN_LOKASI_BEDA', 'Izin Absen di Lokasi Beda'
    TAHUNAN = 'CUTI_TAHUNAN', 'Cuti Tahunan'
    SAKIT = 'CUTI_SAKIT', 'Cuti Sakit'
    DUKA_CITA = 'CUTI_DUKA_CITA', 'Cuti Duka Cita'
    MELAHIRKAN = 'CUTI_MELAHIRKAN', 'Cuti Melahirkan'
    ISTRI_MELAHIRKAN = 'CUTI_ISTRI_MELAHIRKAN', 'Cuti Istri Melahirkan'
    MENIKAH = 'CUTI_MENIKAH', 'Cuti Menikah'
    ANAK_MENIKAH = 'CUTI_ANAK_MENIKAH', 'Cuti Anak Menikah'
    KHITANAN_ANAK = 'CUTI_KHITANAN_ANAK', 'Cuti Khitanan Anak'
    PEMBAPTISAN_ANAK = 'CUTI_PEMBAPTISAN_ANAK', 'Cuti Pembaptisan Anak'


class StatusPermohonanCuti(models.TextChoices):
    MENUNGGU_SUPERVISOR = 'MENUNGGU_SUPERVISOR', 'Menunggu Izin Supervisor'
    MENUNGGU_HRD = 'MENUNGGU_HRD', 'Menunggu Izin HRD'
    DITOLAK = 'DITOLAK', 'Request Ditolak'
    DIBATALKAN = 'DIBATALKAN', 'Dibatalkan'
    APPROVED = 'APPROVED', 'Approved'


# States from which the workflow can still progress or be cancelled.
ACTIVE_STATUSES = {
    StatusPermohonanCuti.MENUNGGU_SUPERVISOR,
    StatusPermohonanCuti.MENUNGGU_HRD,
}


class PermohonanCuti(models.Model):
    # Workflow and Range Data
    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.PROTECT, related_name='permohonan_cuti'
    )
    tipe = models.CharField(max_length=32, choices=TipeCuti.choices)
    alasan = models.TextField(blank=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=StatusPermohonanCuti.choices,
        default=StatusPermohonanCuti.MENUNGGU_SUPERVISOR,
    )
    supervisor = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='cuti_disupervisi',
        null=True,
        blank=True,
    )
    hrd_approver = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.PROTECT,
        related_name='cuti_diapprove_hrd',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = 'Permohonan Cuti'
        ordering = ['-tanggal_mulai']

    def __str__(self):
        return f'{self.karyawan} - {self.get_tipe_display()} ({self.tanggal_mulai} s/d {self.tanggal_selesai})'


class Cuti(models.Model):
    permohonan = models.ForeignKey(
        PermohonanCuti, on_delete=models.CASCADE, related_name='hari_cuti'
    )
    tanggal = models.DateField()

    class Meta:
        verbose_name_plural = 'Cuti'
        ordering = ['-tanggal']

    @property
    def karyawan(self):
        return self.permohonan.karyawan

    @property
    def tipe(self):
        return self.permohonan.tipe

    def __str__(self):
        return f'{self.karyawan} - {self.permohonan.get_tipe_display()} @ {self.tanggal}'
