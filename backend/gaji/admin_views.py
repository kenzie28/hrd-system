"""Admin API for starting, polling, and downloading a Proses Gaji run."""
from django.db import connection, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from karyawan.models import Karyawan
from karyawan.permissions import IsAdminAllowed

from .access import HasGajiPassword
from .jobs import enqueue_proses_gaji
from .models import ProsesGajiJob, StatusProsesGaji
from .services import export_gaji_csv, gaji_for_month, parse_bulan

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
    permission_classes = [IsAdminAllowed, HasGajiPassword]

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
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def get(self, request, pk):
        job = get_object_or_404(ProsesGajiJob, pk=pk)
        return Response(serialize_job(job))


def _periode_from_query(request):
    try:
        return parse_bulan(request.query_params.get('bulan'))
    except ValueError as exc:
        return exc


_GAJI_KARYAWAN_FIELDS = (
    'karyawan_id',
    'nama',
    'level',
    'jabatan',
    'no_bpjs',
    'base_gaji',
    'gaji_bulanan',
    'absensi_dihitung',
)


class AdminGajiKaryawanListView(APIView):
    """Every employee with the wage fields used by this module."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def get(self, request):
        rows = Karyawan.objects.order_by('karyawan_id').values(*_GAJI_KARYAWAN_FIELDS)
        return Response(list(rows))


class AdminGajiKaryawanDetailView(APIView):
    """Turn attendance deductions on or off for one employee."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def patch(self, request, pk):
        karyawan = get_object_or_404(Karyawan, pk=pk)
        value = request.data.get('absensi_dihitung', None)
        if not isinstance(value, bool):
            return Response(
                {'detail': 'absensi_dihitung harus true atau false.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        karyawan.absensi_dihitung = value
        karyawan.save(update_fields=['absensi_dihitung'])
        row = Karyawan.objects.filter(pk=karyawan.pk).values(*_GAJI_KARYAWAN_FIELDS).get()
        return Response(row)


class AdminGajiMonthView(APIView):
    """How many payroll rows exist for a month."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def get(self, request):
        periode = _periode_from_query(request)
        if isinstance(periode, ValueError):
            return Response({'detail': str(periode)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'bulan': f'{periode:%Y-%m}',
                'count': gaji_for_month(periode).count(),
            }
        )


class AdminGajiExportView(APIView):
    """Download every employee's payroll row for one month."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def get(self, request):
        periode = _periode_from_query(request)
        if isinstance(periode, ValueError):
            return Response({'detail': str(periode)}, status=status.HTTP_400_BAD_REQUEST)
        if not gaji_for_month(periode).exists():
            return Response(
                {'detail': 'Belum ada gaji untuk bulan ini.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        csv_text = export_gaji_csv(periode)
        filename = f'gaji-{periode:%Y-%m}.csv'
        response = HttpResponse(csv_text, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
