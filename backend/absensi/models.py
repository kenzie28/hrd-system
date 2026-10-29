from datetime import datetime

from django.db import models


def absensi_minute_key(karyawan_id, lokasi_id, tanggal, jam_masuk, durasi):
    """Identity of one punch down to the minute.

    Seconds on jam masuk and jam keluar do not distinguish rows. Jam keluar is
    the clock time jam masuk + durasi, so an overnight span stays distinct from
    a same-day span that ends at the same clock minute.
    """
    start = datetime.combine(tanggal, jam_masuk)
    end = start + durasi
    return (
        karyawan_id,
        lokasi_id,
        tanggal,
        start.replace(second=0, microsecond=0),
        end.replace(second=0, microsecond=0),
    )


class AbsensiQuerySet(models.QuerySet):
    def same_minute(self, *, karyawan, lokasi, tanggal, jam_masuk, durasi):
        """Return the kept row when this punch matches an existing one to the minute."""
        karyawan_id = getattr(karyawan, 'pk', karyawan)
        lokasi_id = getattr(lokasi, 'pk', lokasi)
        key = absensi_minute_key(karyawan_id, lokasi_id, tanggal, jam_masuk, durasi)
        for row in self.filter(
            karyawan_id=karyawan_id, lokasi_id=lokasi_id, tanggal=tanggal
        ):
            if row.minute_key() == key:
                return row
        return None


class Absensi(models.Model):
    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='absensi'
    )
    lokasi = models.ForeignKey(
        'lokasi.Lokasi', on_delete=models.CASCADE, related_name='absensi'
    )
    tanggal = models.DateField()
    jam_masuk = models.TimeField()
    durasi = models.DurationField()

    objects = AbsensiQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Absensi'
        ordering = ['-tanggal', 'karyawan__nama']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'lokasi', 'tanggal', 'jam_masuk', 'durasi'],
                name='absensi_unique_exact_entry',
            ),
        ]

    def minute_key(self):
        return absensi_minute_key(
            self.karyawan_id, self.lokasi_id, self.tanggal, self.jam_masuk, self.durasi
        )

    def save(self, *args, **kwargs):
        """Keep one row when a new punch matches an existing one to the minute.

        Same karyawan, lokasi, and tanggal are required. Seconds on jam masuk
        and jam keluar are ignored. The first stored row is left unchanged.
        """
        if self._state.adding and None not in (
            self.karyawan_id,
            self.lokasi_id,
            self.tanggal,
            self.jam_masuk,
            self.durasi,
        ):
            existing = type(self).objects.same_minute(
                karyawan=self.karyawan_id,
                lokasi=self.lokasi_id,
                tanggal=self.tanggal,
                jam_masuk=self.jam_masuk,
                durasi=self.durasi,
            )
            if existing is not None:
                self.pk = existing.pk
                self.karyawan_id = existing.karyawan_id
                self.lokasi_id = existing.lokasi_id
                self.tanggal = existing.tanggal
                self.jam_masuk = existing.jam_masuk
                self.durasi = existing.durasi
                self._state.adding = False
                self._state.db = existing._state.db
                self._squashed = True
                return
        super().save(*args, **kwargs)

    @property
    def jam_keluar(self):
        keluar = datetime.combine(self.tanggal, self.jam_masuk) + self.durasi
        return keluar.time()

    @property
    def keluar_hari_offset(self) -> int:
        """Calendar days after tanggal when jam keluar occurs (0 = same day)."""
        keluar = datetime.combine(self.tanggal, self.jam_masuk) + self.durasi
        return (keluar.date() - self.tanggal).days

    def __str__(self):
        return f'{self.karyawan} @ {self.tanggal} {self.jam_masuk:%H:%M}'


class RekapAbsensi(models.Model):
    """Monthly attendance summary for one employee, produced by Proses Absensi."""

    month = models.DateField(help_text='First day of the processed month.')
    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='rekap_absensi'
    )
    hari_hadir = models.PositiveIntegerField(default=0)
    hari_telat = models.PositiveIntegerField(default=0)
    hari_alpa = models.PositiveIntegerField(default=0)
    hari_keluar_cepat = models.PositiveIntegerField(default=0)
    total_menit_telat = models.PositiveIntegerField(default=0)
    total_menit_lembur = models.PositiveIntegerField(default=0)
    materialized_through = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Rekap Absensi'
        ordering = ['-month', 'karyawan__nama']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'month'],
                name='rekap_absensi_unique_karyawan_month',
            ),
        ]

    def __str__(self):
        return f'{self.karyawan} — {self.month:%Y-%m}'


class StatusKehadiran(models.TextChoices):
    HADIR = 'HADIR', 'Hadir'
    CUTI = 'CUTI', 'Cuti'
    ALPA = 'ALPA', 'Alpa'


class Kehadiran(models.Model):
    """One scheduled day: the home shift, plus the punch and/or leave that apply.

    A full-day leave has no Absensi and points at Cuti instead.
    """

    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='kehadiran'
    )
    tanggal = models.DateField()
    absensi = models.OneToOneField(
        'Absensi',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='kehadiran',
    )
    cuti = models.ForeignKey(
        'cuti.Cuti',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kehadiran',
    )
    permohonan_lembur = models.ForeignKey(
        'lembur.PermohonanLembur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kehadiran',
    )
    shift = models.ForeignKey(
        'shift.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kehadiran',
    )
    menit_telat = models.PositiveIntegerField(default=0)
    cepat_keluar = models.PositiveIntegerField(default=0)
    lembur = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=8, choices=StatusKehadiran.choices)

    class Meta:
        verbose_name_plural = 'Kehadiran'
        ordering = ['-tanggal', 'karyawan__nama', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'tanggal'],
                name='kehadiran_unique_karyawan_tanggal',
            ),
        ]

    def __str__(self):
        return f'{self.karyawan} — {self.tanggal} ({self.get_status_display()})'


class CatatanRekapAbsensi(models.Model):
    """One Indonesian note about a day (or the month) in a RekapAbsensi."""

    rekap = models.ForeignKey(
        RekapAbsensi, on_delete=models.CASCADE, related_name='catatan'
    )
    tanggal = models.DateField(null=True, blank=True)
    pesan = models.TextField()

    class Meta:
        verbose_name_plural = 'Catatan Rekap Absensi'
        ordering = ['tanggal', 'id']

    def __str__(self):
        when = self.tanggal.isoformat() if self.tanggal else 'bulan'
        return f'{when}: {self.pesan}'


class PendingAttendanceDay(models.Model):
    """A durable request to rematerialize one employee/day."""

    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='+'
    )
    tanggal = models.DateField()
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tanggal', 'karyawan_id']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'tanggal'],
                name='pending_attendance_day_unique_key',
            ),
        ]


class PendingAttendanceMonth(models.Model):
    """A durable request to re-aggregate one employee/month."""

    karyawan = models.ForeignKey(
        'karyawan.Karyawan', on_delete=models.CASCADE, related_name='+'
    )
    month = models.DateField(help_text='First day of the affected month.')
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['month', 'karyawan_id']
        constraints = [
            models.UniqueConstraint(
                fields=['karyawan', 'month'],
                name='pending_attendance_month_unique_key',
            ),
        ]
