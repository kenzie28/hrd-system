"""Run Proses Gaji off the request so a long month does not hit the proxy timeout."""
from __future__ import annotations

import threading

from django.db import close_old_connections, transaction
from django.utils import timezone

from karyawan.models import Karyawan

from .models import ProsesGajiJob, StatusProsesGaji
from .services import write_gaji


def run_proses_gaji(job_id: int) -> None:
    """Process every employee for the job's month, updating progress as it goes."""
    close_old_connections()
    try:
        job = ProsesGajiJob.objects.get(pk=job_id)
        if job.status in (StatusProsesGaji.SUCCEEDED, StatusProsesGaji.FAILED):
            return
        ids = list(
            Karyawan.objects.order_by('nama', 'karyawan_id').values_list(
                'pk', flat=True
            )
        )
        ProsesGajiJob.objects.filter(pk=job_id).update(
            status=StatusProsesGaji.RUNNING,
            total=len(ids),
            processed=0,
            message='',
            finished_at=None,
        )
        periode = job.periode
        for index, karyawan_id in enumerate(ids, start=1):
            karyawan = Karyawan.objects.get(pk=karyawan_id)
            try:
                with transaction.atomic():
                    write_gaji(karyawan, periode)
            except Exception as exc:
                ProsesGajiJob.objects.filter(pk=job_id).update(
                    status=StatusProsesGaji.FAILED,
                    processed=index - 1,
                    message=(
                        f'Gagal memproses {karyawan.nama} ({karyawan_id}): {exc}'
                    ),
                    finished_at=timezone.now(),
                )
                return
            ProsesGajiJob.objects.filter(pk=job_id).update(processed=index)
        ProsesGajiJob.objects.filter(pk=job_id).update(
            status=StatusProsesGaji.SUCCEEDED,
            message=f'Gaji {periode:%Y-%m} selesai untuk {len(ids)} karyawan.',
            finished_at=timezone.now(),
        )
    except Exception as exc:
        ProsesGajiJob.objects.filter(pk=job_id).update(
            status=StatusProsesGaji.FAILED,
            message=str(exc),
            finished_at=timezone.now(),
        )
    finally:
        close_old_connections()


def enqueue_proses_gaji(job_id: int) -> None:
    """Start the payroll run in this worker. Progress is stored on the job row."""
    threading.Thread(
        target=run_proses_gaji,
        args=(job_id,),
        daemon=True,
    ).start()
