"""Admin API for starting and polling a Proses Gaji job."""
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from karyawan.permissions import IsAdminAllowed

from .jobs import enqueue_proses_gaji
from .models import ProsesGajiJob, StatusProsesGaji
from .services import parse_bulan

_OPEN_STATUSES = (StatusProsesGaji.PENDING, StatusProsesGaji.RUNNING)


def serialize_job(job: ProsesGajiJob) -> dict:
    return {
        'id': job.pk,
        'periode': job.periode.isoformat(),
        'bulan': f'{job.periode:%Y-%m}',
        'status': job.status,
        'total': job.total,
        'processed': job.processed,
        'message': job.message,
    }


def _start_or_attach(periode):
    with transaction.atomic():
        locked = ProsesGajiJob.objects.filter(periode=periode).order_by('pk')
        if connection.features.has_select_for_update:
            locked = locked.select_for_update()
        list(locked)
        existing = (
            ProsesGajiJob.objects.filter(periode=periode, status__in=_OPEN_STATUSES)
            .order_by('-pk')
            .first()
        )
        if existing is not None:
            return existing, False
        return ProsesGajiJob.objects.create(periode=periode), True


class AdminProsesGajiView(APIView):
    """Start Proses Gaji for a month, or return the job already running."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def post(self, request):
        try:
            periode = parse_bulan(request.data.get('bulan'))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        job, created = _start_or_attach(periode)
        if created:
            enqueue_proses_gaji(job.pk)
        return Response(serialize_job(job), status=status.HTTP_202_ACCEPTED)


class AdminProsesGajiDetailView(APIView):
    """Poll one Proses Gaji job."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def get(self, request, pk):
        job = get_object_or_404(ProsesGajiJob, pk=pk)
        return Response(serialize_job(job))
