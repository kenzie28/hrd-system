from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_error, debug_exception
from karyawan.permissions import IsAdminAllowed

from .models import Koreksi
from .serializers import KoreksiSerializer
from .services import (
    KoreksiImportError,
    KoreksiImportResult,
    import_koreksi_csv,
    serialize_koreksi_import_result,
)


def _apply_common_filters(queryset, params):
    """Filter by ?karyawan_id=<id> and ?bulan=YYYY-MM."""
    karyawan_id = params.get('karyawan_id')
    if karyawan_id:
        queryset = queryset.filter(karyawan_id=karyawan_id)
    bulan = params.get('bulan')
    if bulan:
        year, month = map(int, bulan.split('-'))
        queryset = queryset.filter(bulan__year=year, bulan__month=month)
    return queryset


class AdminKoreksiViewSet(viewsets.ReadOnlyModelViewSet):
    """HRD review list of imported corrections (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = KoreksiSerializer

    def get_queryset(self):
        qs = Koreksi.objects.select_related('karyawan')
        return _apply_common_filters(qs, self.request.query_params)


class AdminKoreksiImportView(APIView):
    """CSV upload endpoint: columns karyawan_id,tipe,nominal,bulan."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            debug_error(
                'koreksi_import_post',
                'Request tanpa file CSV.',
                content_type=request.content_type,
                hint='Kirim multipart/form-data dengan field "file" berisi CSV.',
            )
            return Response(
                serialize_koreksi_import_result(
                    KoreksiImportResult(
                        errors=[
                            KoreksiImportError(0, 'File CSV wajib diunggah.'),
                        ],
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_koreksi_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'koreksi_import_post',
                'Import CSV gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = KoreksiImportResult(
                errors=[
                    KoreksiImportError(
                        0,
                        f'Gagal menyimpan data ke database: {exc}',
                    ),
                ],
            )
        except Exception as exc:
            debug_exception(
                'koreksi_import_post',
                'Import CSV gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
                size=getattr(upload, 'size', None),
            )
            result = KoreksiImportResult(
                errors=[
                    KoreksiImportError(
                        0,
                        f'Import gagal: {exc}',
                    ),
                ],
            )

        if not result.ok:
            debug_error(
                'koreksi_import_post',
                'Import selesai dengan error validasi — tidak ada data disimpan.',
                filename=getattr(upload, 'name', None),
                total_rows=result.total_rows,
                error_count=len(result.errors),
            )

        return Response(
            serialize_koreksi_import_result(result),
            status=status.HTTP_200_OK,
        )
