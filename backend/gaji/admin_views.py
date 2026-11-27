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
from .bank_transfer import export_gaji_bank_transfer_xlsx
from .jobs import enqueue_proses_gaji
from .models import ProsesGajiJob, StatusProsesGaji
from .services import gaji_for_month, parse_bulan

_XLSX_CONTENT_TYPE = (
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

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
    'target_gaji',
    'bca_transfer',
    'absensi_dihitung',
    'lembur_dibayar',
)

_EDITABLE_GAJI_KARYAWAN_FIELDS = frozenset(
    {
        'nama',
        'level',
        'jabatan',
        'no_bpjs',
        'base_gaji',
        'gaji_bulanan',
        'target_gaji',
        'bca_transfer',
        'absensi_dihitung',
        'lembur_dibayar',
    }
)

_NULLABLE_WAGE_FIELDS = frozenset({'target_gaji', 'bca_transfer'})

_BOOLEAN_GAJI_KARYAWAN_FIELDS = frozenset({'absensi_dihitung', 'lembur_dibayar'})

# Same ceiling as the wage CSV import.
_WAGE_MAX = (1 << 63) - 1


def _gaji_karyawan_row(karyawan_id):
    return Karyawan.objects.filter(pk=karyawan_id).values(*_GAJI_KARYAWAN_FIELDS).get()


def _clean_text(value, *, label, max_length, required):
    if not isinstance(value, str):
        return None, f'{label} harus teks.'
    text = value.strip()
    if required and not text:
        return None, f'{label} wajib diisi.'
    if len(text) > max_length:
        return None, f'{label} maksimal {max_length} karakter.'
    return text, None


def _clean_gaji_karyawan_value(field, value):
    if field == 'nama':
        return _clean_text(value, label='Nama', max_length=128, required=True)
    if field == 'jabatan':
        return _clean_text(value, label='Jabatan', max_length=128, required=False)
    if field == 'no_bpjs':
        return _clean_text(value, label='No. BPJS', max_length=16, required=False)
    if field == 'level':
        # bool is an int in Python, so reject it before the range check.
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9:
            return None, 'Level harus bilangan 0 sampai 9.'
        return value, None
    if field in ('base_gaji', 'gaji_bulanan'):
        label = 'Base gaji' if field == 'base_gaji' else 'Gaji bulanan'
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > _WAGE_MAX
        ):
            return None, f'{label} harus bilangan bulat non-negatif.'
        return value, None
    if field in _NULLABLE_WAGE_FIELDS:
        label = 'Target gaji' if field == 'target_gaji' else 'BCA transfer'
        if value is None:
            return None, None
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > _WAGE_MAX
        ):
            return None, f'{label} harus bilangan bulat non-negatif atau kosong.'
        return value, None
    if field in _BOOLEAN_GAJI_KARYAWAN_FIELDS:
        if not isinstance(value, bool):
            return None, f'{field} harus true atau false.'
        return value, None
    return None, f'Field tidak dikenal: {field}.'


def _clean_gaji_karyawan_updates(data):
    """Validate a partial update. `password` is the module gate, not a field."""
    if not isinstance(data, dict):
        return None, 'Data tidak valid.'
    payload = {key: value for key, value in data.items() if key != 'password'}
    unknown = sorted(key for key in payload if key not in _EDITABLE_GAJI_KARYAWAN_FIELDS)
    if unknown:
        return None, f'Field tidak dikenal: {", ".join(unknown)}.'
    if not payload:
        return None, 'Tidak ada data yang diubah.'

    cleaned = {}
    errors = []
    for field, value in payload.items():
        parsed, error = _clean_gaji_karyawan_value(field, value)
        if error:
            errors.append(error)
        else:
            cleaned[field] = parsed
    if errors:
        return None, ' '.join(errors)
    return cleaned, None


class AdminGajiKaryawanListView(APIView):
    """Every employee with the wage fields used by this module."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def get(self, request):
        rows = Karyawan.objects.order_by('karyawan_id').values(*_GAJI_KARYAWAN_FIELDS)
        return Response(list(rows))


class AdminGajiKaryawanDetailView(APIView):
    """Update any wage field for one employee. Omitted fields stay as they are."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def patch(self, request, pk):
        karyawan = get_object_or_404(Karyawan, pk=pk)
        updates, error = _clean_gaji_karyawan_updates(request.data)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        for field, value in updates.items():
            setattr(karyawan, field, value)
        karyawan.save(update_fields=list(updates))
        return Response(_gaji_karyawan_row(karyawan.pk))


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
        content = export_gaji_bank_transfer_xlsx(periode)
        filename = f'Bank-Transfer-{periode:%m-%Y}.xlsx'
        response = HttpResponse(content, content_type=_XLSX_CONTENT_TYPE)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
