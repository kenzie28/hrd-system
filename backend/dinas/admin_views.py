from datetime import datetime

from django.db import IntegrityError
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_exception
from karyawan.models import Karyawan
from karyawan.permissions import IsAdminAllowed

from .models import Dinas
from .serializers import DinasSerializer
from .services import (
    DinasImportError,
    DinasImportResult,
    DinasRangeError,
    create_dinas_range,
    import_dinas_csv,
    serialize_dinas_import_result,
)


def _body(data):
    if not isinstance(data, dict):
        return None, Response(
            {'detail': 'Body harus berupa objek.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return data, None


def _karyawan(data):
    karyawan_id = data.get('karyawan_id')
    if not isinstance(karyawan_id, str) or not karyawan_id.strip():
        return None, Response(
            {'karyawan_id': 'karyawan_id wajib diisi.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    karyawan = Karyawan.objects.filter(pk=karyawan_id.strip()).first()
    if karyawan is None:
        return None, Response(
            {'karyawan_id': 'Karyawan tidak ditemukan.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return karyawan, None


def _parse_date(value, field):
    parsed = None
    if isinstance(value, str):
        try:
            parsed = datetime.strptime(value.strip(), '%Y-%m-%d').date()
        except ValueError:
            parsed = None
    if parsed is None:
        return None, Response(
            {field: f'{field} harus format yyyy-mm-dd.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return parsed, None


class AdminDinasViewSet(
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """HRD list and delete for assigned dinas days."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = DinasSerializer

    def get_queryset(self):
        qs = Dinas.objects.select_related('karyawan')
        karyawan_id = self.request.query_params.get('karyawan_id')
        if karyawan_id:
            qs = qs.filter(karyawan_id=karyawan_id)
        bulan = self.request.query_params.get('bulan')
        if bulan:
            year, month = map(int, bulan.split('-'))
            qs = qs.filter(tanggal__year=year, tanggal__month=month)
        return qs

    @action(detail=False, methods=['post'], url_path='range')
    def date_range(self, request):
        """Create dinas for every day in a date range."""
        data, error = _body(request.data)
        if error is not None:
            return error
        karyawan, error = _karyawan(data)
        if error is not None:
            return error
        tanggal_mulai, error = _parse_date(data.get('tanggal_mulai'), 'tanggal_mulai')
        if error is not None:
            return error
        tanggal_selesai, error = _parse_date(
            data.get('tanggal_selesai'), 'tanggal_selesai'
        )
        if error is not None:
            return error
        try:
            created, skipped = create_dinas_range(karyawan, tanggal_mulai, tanggal_selesai)
        except DinasRangeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'created': created,
                'skipped': skipped,
                'tanggal_mulai': tanggal_mulai.isoformat(),
                'tanggal_selesai': tanggal_selesai.isoformat(),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AdminDinasImportView(APIView):
    """Import dinas days. Columns: karyawan_id, tanggal."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                serialize_dinas_import_result(
                    DinasImportResult(
                        errors=[DinasImportError(0, 'File CSV wajib diunggah.')]
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_dinas_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'dinas_import_post',
                'Import CSV dinas gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = DinasImportResult(
                errors=[DinasImportError(0, f'Gagal menyimpan data ke database: {exc}')]
            )
        except Exception as exc:
            debug_exception(
                'dinas_import_post',
                'Import CSV dinas gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = DinasImportResult(
                errors=[DinasImportError(0, f'Import gagal: {exc}')]
            )

        return Response(
            serialize_dinas_import_result(result),
            status=status.HTTP_200_OK,
        )
