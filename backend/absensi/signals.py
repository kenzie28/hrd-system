"""ORM/admin safety-net invalidation for attendance source models."""
from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from cuti.models import Cuti, PermohonanCuti
from karyawan.models import Karyawan
from lembur.models import PermohonanLembur
from liburan.models import Liburan
from shift.models import Shift

from .invalidation import (
    enqueue_days,
    enqueue_holiday_days,
    enqueue_location_changes,
    enqueue_shift_shapes,
    signal_invalidation_suppressed,
)
from .models import Absensi


def _remember_old(sender, instance, fields):
    if not instance.pk:
        instance._attendance_old = None
        return
    instance._attendance_old = sender.objects.filter(pk=instance.pk).values(
        *fields
    ).first()


def _enqueue_keys(keys):
    if signal_invalidation_suppressed():
        return
    enqueue_days(keys)


@receiver(pre_save, sender=Absensi)
def absensi_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('karyawan_id', 'tanggal'))


@receiver(post_save, sender=Absensi)
def absensi_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    old = getattr(instance, '_attendance_old', None)
    keys = [(instance.karyawan_id, instance.tanggal)]
    if old:
        keys.append((old['karyawan_id'], old['tanggal']))
    _enqueue_keys(keys)


@receiver(post_delete, sender=Absensi)
def absensi_post_delete(sender, instance, **kwargs):
    _enqueue_keys([(instance.karyawan_id, instance.tanggal)])


@receiver(pre_save, sender=Cuti)
def cuti_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('permohonan_id', 'tanggal'))


def _cuti_key(permohonan_id, day):
    karyawan_id = (
        PermohonanCuti.objects.filter(pk=permohonan_id)
        .values_list('karyawan_id', flat=True)
        .first()
    )
    return karyawan_id, day


@receiver(post_save, sender=Cuti)
def cuti_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    keys = [_cuti_key(instance.permohonan_id, instance.tanggal)]
    old = getattr(instance, '_attendance_old', None)
    if old:
        keys.append(_cuti_key(old['permohonan_id'], old['tanggal']))
    _enqueue_keys(keys)


@receiver(post_delete, sender=Cuti)
def cuti_post_delete(sender, instance, **kwargs):
    _enqueue_keys([(instance.permohonan.karyawan_id, instance.tanggal)])


@receiver(pre_save, sender=PermohonanCuti)
def permohonan_cuti_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('karyawan_id',))


@receiver(post_save, sender=PermohonanCuti)
def permohonan_cuti_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    old = getattr(instance, '_attendance_old', None)
    employee_ids = {instance.karyawan_id}
    if old:
        employee_ids.add(old['karyawan_id'])
    days = instance.hari_cuti.values_list('tanggal', flat=True)
    _enqueue_keys((employee_id, day) for employee_id in employee_ids for day in days)


@receiver(pre_save, sender=PermohonanLembur)
def lembur_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('karyawan_id', 'tanggal'))


@receiver(post_save, sender=PermohonanLembur)
def lembur_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    old = getattr(instance, '_attendance_old', None)
    keys = [(instance.karyawan_id, instance.tanggal)]
    if old:
        keys.append((old['karyawan_id'], old['tanggal']))
    _enqueue_keys(keys)


@receiver(post_delete, sender=PermohonanLembur)
def lembur_post_delete(sender, instance, **kwargs):
    _enqueue_keys([(instance.karyawan_id, instance.tanggal)])


@receiver(pre_save, sender=Liburan)
def liburan_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('tanggal',))


def _enqueue_holiday(day):
    if not signal_invalidation_suppressed():
        enqueue_holiday_days([day])


@receiver(post_save, sender=Liburan)
def liburan_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _enqueue_holiday(instance.tanggal)
    old = getattr(instance, '_attendance_old', None)
    if old and old['tanggal'] != instance.tanggal:
        _enqueue_holiday(old['tanggal'])


@receiver(post_delete, sender=Liburan)
def liburan_post_delete(sender, instance, **kwargs):
    _enqueue_holiday(instance.tanggal)


@receiver(pre_save, sender=Shift)
def shift_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('lokasi_kerja_id', 'hari'))


def _enqueue_shift_shape(lokasi_id, hari):
    if not signal_invalidation_suppressed():
        enqueue_shift_shapes([(lokasi_id, hari)])


@receiver(post_save, sender=Shift)
def shift_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _enqueue_shift_shape(instance.lokasi_kerja_id, instance.hari)
    old = getattr(instance, '_attendance_old', None)
    if old and (
        old['lokasi_kerja_id'], old['hari']
    ) != (instance.lokasi_kerja_id, instance.hari):
        _enqueue_shift_shape(old['lokasi_kerja_id'], old['hari'])


@receiver(post_delete, sender=Shift)
def shift_post_delete(sender, instance, **kwargs):
    _enqueue_shift_shape(instance.lokasi_kerja_id, instance.hari)


@receiver(pre_save, sender=Karyawan)
def karyawan_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, ('lokasi_kerja_id',))


@receiver(post_save, sender=Karyawan)
def karyawan_post_save(sender, instance, created=False, raw=False, **kwargs):
    if raw:
        return
    old = getattr(instance, '_attendance_old', None)
    if not created and old and old['lokasi_kerja_id'] == instance.lokasi_kerja_id:
        return
    if not signal_invalidation_suppressed():
        enqueue_location_changes(
            [
                (
                    instance.pk,
                    old['lokasi_kerja_id'] if old else None,
                    instance.lokasi_kerja_id,
                )
            ]
        )
