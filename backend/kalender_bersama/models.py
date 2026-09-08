from django.db import models


class Langganan(models.Model):
    subscriber = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.CASCADE,
        related_name='langganan',
    )
    target = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.CASCADE,
        related_name='pengikut',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Langganan'
        ordering = ['target__nama', 'target_id']
        constraints = [
            models.UniqueConstraint(
                fields=('subscriber', 'target'),
                name='kalender_bersama_langganan_unique',
            ),
            models.CheckConstraint(
                condition=~models.Q(subscriber=models.F('target')),
                name='kalender_bersama_langganan_not_self',
            ),
        ]

    def __str__(self):
        return f'{self.subscriber_id} → {self.target_id}'


class NotifikasiDismiss(models.Model):
    subscriber = models.ForeignKey(
        'karyawan.Karyawan',
        on_delete=models.CASCADE,
        related_name='notifikasi_dismiss',
    )
    permohonan = models.ForeignKey(
        'cuti.PermohonanCuti',
        on_delete=models.CASCADE,
        related_name='kalender_bersama_dismiss',
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Notifikasi Dismiss'
        ordering = ['-dismissed_at']
        constraints = [
            models.UniqueConstraint(
                fields=('subscriber', 'permohonan'),
                name='kalender_bersama_notifikasi_dismiss_unique',
            ),
        ]

    def __str__(self):
        return f'{self.subscriber_id} dismiss {self.permohonan_id}'
