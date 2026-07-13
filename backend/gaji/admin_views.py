from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_error, debug_exception
from core.permissions import IsAdminAllowed

from .models import GajiTemp
from .serializers import GajiTempSerializer
from .services import (
    GajiImportError,
    GajiImportResult,
    import_gaji_csv,
    serialize_gaji_import_result,
)


def _apply_common_filters(queryset, params):
    """Filter by ?karyawan=<id> and ?bulan=YYYY-MM."""
    karyawan = params.get('karyawan')
    if karyawan:
        queryset = queryset.filter(karyawan_id=karyawan)
    bulan = params.get('bulan')
    if bulan:
        year, month = map(int, bulan.split('-'))
        queryset = queryset.filter(periode__year=year, periode__month=month)
    return queryset


class AdminGajiViewSet(viewsets.ReadOnlyModelViewSet):
    """HRD review list of imported payroll rows (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = GajiTempSerializer

    def get_queryset(self):
        qs = GajiTemp.objects.select_related('karyawan')
        return _apply_common_filters(qs, self.request.query_params)


class AdminGajiImportView(APIView):
    """CSV upload endpoint for HRD to import a month's payroll data."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            debug_error(
                'gaji_import_post',
                'Request tanpa file CSV.',
                content_type=request.content_type,
                hint='Kirim multipart/form-data dengan field "file" berisi CSV.',
            )
            return Response(
                serialize_gaji_import_result(
                    GajiImportResult(
                        errors=[
                            GajiImportError(0, 'File CSV wajib diunggah.'),
                        ],
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        upsert_karyawan = str(request.data.get('upsert_karyawan', 'true')).lower() in (
            'true',
            '1',
            'yes',
        )

        try:
            result = import_gaji_csv(upload, upsert_karyawan=upsert_karyawan)
        except IntegrityError as exc:
            debug_exception(
                'gaji_import_post',
                'Import CSV gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
                upsert_karyawan=upsert_karyawan,
            )
            result = GajiImportResult(
                errors=[
                    GajiImportError(
                        0,
                        f'Gagal menyimpan data ke database: {exc}',
                    ),
                ],
            )
        except Exception as exc:
            debug_exception(
                'gaji_import_post',
                'Import CSV gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
                size=getattr(upload, 'size', None),
                upsert_karyawan=upsert_karyawan,
                hint='Periksa log Cloud Run; aktifkan ./deploy.sh --debug untuk detail lebih lanjut.',
            )
            result = GajiImportResult(
                errors=[
                    GajiImportError(
                        0,
                        f'Import gagal: {exc}',
                    ),
                ],
            )

        if not result.ok:
            debug_error(
                'gaji_import_post',
                'Import selesai dengan error validasi — tidak ada data disimpan.',
                filename=getattr(upload, 'name', None),
                total_rows=result.total_rows,
                error_count=len(result.errors),
                upsert_karyawan=upsert_karyawan,
            )

        return Response(serialize_gaji_import_result(result), status=status.HTTP_200_OK)
