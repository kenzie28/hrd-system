"""Durable attendance invalidation, post-commit draining, and retry."""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, timedelta

from django.db import models, transaction
from django.utils import timezone

from karyawan.models import Karyawan

from .engine import (
    WEEKDAY_TO_HARI,
    aggregate_month,
    closed_through,
    iter_days,
    materialize_day,
    month_start,
)
from .models import PendingAttendanceDay, PendingAttendanceMonth, RekapAbsensi

_drain_lock = threading.Lock()
_signals_suppressed = ContextVar('attendance_invalidation_signals_suppressed', default=False)
logger = logging.getLogger(__name__)


def _schedule_drain() -> None:
    transaction.on_commit(_drain_after_commit)


def _drain_after_commit() -> None:
    try:
        drain_pending()
    except Exception:
        logger.exception('Attendance invalidation drain failed; queued work was retained.')


def schedule_drain() -> None:
    """Schedule one post-commit drain after a caller has enqueued a batch."""
    _schedule_drain()


@contextmanager
def suppress_signal_invalidation():
    """Let a service replace per-row signal work with one consolidated batch."""
    token = _signals_suppressed.set(True)
    try:
        yield
    finally:
        _signals_suppressed.reset(token)


def signal_invalidation_suppressed() -> bool:
    return _signals_suppressed.get()


def enqueue_days(keys, *, drain: bool = True) -> None:
    """Persist unique dirty employee/day keys efficiently."""
    keys = {(str(karyawan_id), day) for karyawan_id, day in keys if karyawan_id and day}
    if not keys:
        return
    employee_ids = set(
        Karyawan.objects.filter(pk__in={key[0] for key in keys}).values_list(
            'pk', flat=True
        )
    )
    keys = {(employee_id, day) for employee_id, day in keys if employee_id in employee_ids}
    PendingAttendanceDay.objects.bulk_create(
        [
            PendingAttendanceDay(karyawan_id=employee_id, tanggal=day)
            for employee_id, day in keys
        ],
        ignore_conflicts=True,
    )
    PendingAttendanceMonth.objects.bulk_create(
        [
            PendingAttendanceMonth(karyawan_id=employee_id, month=month)
            for employee_id, month in {
                (employee_id, month_start(day)) for employee_id, day in keys
            }
        ],
        ignore_conflicts=True,
    )
    if drain:
        _schedule_drain()


def enqueue_day(karyawan_id: str, day: date, *, drain: bool = True) -> None:
    """Persist a unique dirty day in the caller's current transaction."""
    enqueue_days([(karyawan_id, day)], drain=drain)


def enqueue_month(karyawan_id: str, month: date, *, drain: bool = True) -> None:
    """Persist a unique monthly aggregation request."""
    if month.day != 1:
        month = month_start(month)
    PendingAttendanceMonth.objects.get_or_create(
        karyawan_id=karyawan_id, month=month
    )
    if drain:
        _schedule_drain()


def tracked_months() -> set[date]:
    """Months whose attendance can currently need rematerialization."""
    months = set(RekapAbsensi.objects.values_list('month', flat=True))
    months.add(month_start(timezone.localdate()))
    return months


def matching_tracked_days(weekday: int, *, today: date | None = None):
    today = today or timezone.localdate()
    for month in tracked_months():
        cutoff = closed_through(month, today)
        if cutoff is None:
            continue
        for day in iter_days(month, cutoff):
            if day.weekday() == weekday:
                yield day


def all_tracked_days(*, today: date | None = None):
    today = today or timezone.localdate()
    for month in tracked_months():
        cutoff = closed_through(month, today)
        if cutoff is not None:
            yield from iter_days(month, cutoff)


def enqueue_holiday_days(days, *, drain: bool = True) -> None:
    enqueue_days(expand_holiday_days(days), drain=drain)


def expand_holiday_days(days) -> set[tuple[str, date]]:
    days = set(days)
    employee_ids = Karyawan.objects.values_list('pk', flat=True)
    return {
        (employee_id, day) for employee_id in employee_ids for day in days
    }


def expand_shift_shapes(shapes) -> set[tuple[str, date]]:
    """Expand (location id, HariKerja value) pairs to dirty keys."""
    keys = []
    for location_id, hari in set(shapes):
        if not location_id or not hari:
            continue
        weekday = next(key for key, value in WEEKDAY_TO_HARI.items() if value == hari)
        employee_ids = Karyawan.objects.filter(
            lokasi_kerja_id=location_id
        ).values_list('pk', flat=True)
        days = list(matching_tracked_days(weekday))
        keys.extend(
            (employee_id, day) for employee_id in employee_ids for day in days
        )
    return set(keys)


def enqueue_shift_shapes(shapes, *, drain: bool = True) -> None:
    enqueue_days(expand_shift_shapes(shapes), drain=drain)


def expand_location_changes(changes) -> set[tuple[str, date]]:
    """Expand changed employee locations to all tracked dirty keys."""
    employee_ids = {
        str(employee_id)
        for employee_id, old_location_id, new_location_id in changes
        if old_location_id != new_location_id
    }
    days = list(all_tracked_days())
    return {(employee_id, day) for employee_id in employee_ids for day in days}


def enqueue_location_changes(changes, *, drain: bool = True) -> None:
    enqueue_days(expand_location_changes(changes), drain=drain)


def expand_employee_months(employee_ids, months, *, today: date | None = None):
    """Expand employees and month starts to all closed dates in those months."""
    today = today or timezone.localdate()
    keys = set()
    for month in set(months):
        month = month_start(month)
        cutoff = closed_through(month, today)
        if cutoff is not None:
            keys.update(
                (str(employee_id), day)
                for employee_id in employee_ids
                for day in iter_days(month, cutoff)
            )
    return keys


def _record_day_failure(ids: list[int], exc: Exception) -> None:
    PendingAttendanceDay.objects.filter(pk__in=ids).update(
        attempts=models.F('attempts') + 1,
        last_error=str(exc)[:4000],
    )


def _record_month_failure(ids: list[int], exc: Exception) -> None:
    PendingAttendanceMonth.objects.filter(pk__in=ids).update(
        attempts=models.F('attempts') + 1,
        last_error=str(exc)[:4000],
    )


def drain_pending(*, today: date | None = None) -> dict[str, int]:
    """Drain closed work. Failed and open-date keys remain available for retry."""
    # on_commit callbacks may converge from several writes in the same request.
    if not _drain_lock.acquire(blocking=False):
        return {'days': 0, 'months': 0, 'failed': 0}
    try:
        today = today or timezone.localdate()
        result = {'days': 0, 'months': 0, 'failed': 0}
        groups: dict[tuple[str, date], list[PendingAttendanceDay]] = defaultdict(list)
        pending_days = list(
            PendingAttendanceDay.objects.filter(tanggal__lt=today)
            .select_related('karyawan__lokasi_kerja')
            .order_by('tanggal', 'karyawan_id')
        )
        for item in pending_days:
            groups[(item.karyawan_id, month_start(item.tanggal))].append(item)

        processed_month_keys = set()
        for key, items in groups.items():
            ids = [item.pk for item in items]
            try:
                with transaction.atomic():
                    notes = {}
                    karyawan = items[0].karyawan
                    for item in items:
                        _outcome, evaluation = materialize_day(
                            karyawan, item.tanggal, today=today
                        )
                        notes[item.tanggal] = evaluation.notes
                    aggregate_month(
                        karyawan,
                        key[1],
                        today=today,
                        notes_by_day=notes,
                    )
                    PendingAttendanceDay.objects.filter(pk__in=ids).delete()
                    PendingAttendanceMonth.objects.filter(
                        karyawan_id=key[0], month=key[1]
                    ).delete()
                result['days'] += len(items)
                result['months'] += 1
                processed_month_keys.add(key)
            except Exception as exc:  # keep durable work for a later retry
                _record_day_failure(ids, exc)
                result['failed'] += len(items)

        pending_months = list(
            PendingAttendanceMonth.objects.select_related(
                'karyawan__lokasi_kerja'
            ).order_by('month', 'karyawan_id')
        )
        for item in pending_months:
            key = (item.karyawan_id, item.month)
            if key in processed_month_keys:
                continue
            try:
                with transaction.atomic():
                    aggregate_month(item.karyawan, item.month, today=today)
                    PendingAttendanceMonth.objects.filter(pk=item.pk).delete()
                result['months'] += 1
            except Exception as exc:  # keep durable work for a later retry
                _record_month_failure([item.pk], exc)
                result['failed'] += 1
        return result
    finally:
        _drain_lock.release()


def close_yesterday(*, today: date | None = None) -> dict[str, int]:
    """Create no-input alpa work for yesterday, then retry all pending work."""
    today = today or timezone.localdate()
    yesterday = today - timedelta(days=1)
    with transaction.atomic():
        enqueue_days(
            (
                (karyawan_id, yesterday)
                for karyawan_id in Karyawan.objects.values_list('pk', flat=True)
            ),
            drain=False,
        )
    return drain_pending(today=today)
