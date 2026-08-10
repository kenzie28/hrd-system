from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_error, debug_exception
from karyawan.permissions import IsAdminAllowed

from .models import Liburan
from .serializers import LiburanSerializer
from .services import (
    LiburanImportError,
    LiburanImportResult,
    import_liburan_csv,
    serialize_liburan_import_result,
)


class AdminLiburanViewSet(viewsets.ModelViewSet):
    """HRD full CRUD for holiday records (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = LiburanSerializer

    def get_queryset(self):
        qs = Liburan.objects.all()
        bulan = self.request.query_params.get('bulan')
        if bulan:
            year, month = map(int, bulan.split('-'))
            qs = qs.filter(tanggal__year=year, tanggal__month=month)
        return qs


class AdminLiburanImportView(APIView):
    """CSV upload endpoint: columns nama,tanggal (yyyy-mm-dd)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            debug_error(
                'liburan_import_post',
                'Request tanpa file CSV.',
                content_type=request.content_type,
                hint='Kirim multipart/form-data dengan field "file" berisi CSV.',
            )
            return Response(
                serialize_liburan_import_result(
                    LiburanImportResult(
                        errors=[
                            LiburanImportError(0, 'File CSV wajib diunggah.'),
                        ],
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_liburan_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'liburan_import_post',
                'Import CSV gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = LiburanImportResult(
                errors=[
                    LiburanImportError(
                        0,
                        f'Gagal menyimpan data ke database: {exc}',
                    ),
                ],
            )
        except Exception as exc:
            debug_exception(
                'liburan_import_post',
                'Import CSV gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
                size=getattr(upload, 'size', None),
            )
            result = LiburanImportResult(
                errors=[
                    LiburanImportError(
                        0,
                        f'Import gagal: {exc}',
                    ),
                ],
            )

        if not result.ok:
            debug_error(
                'liburan_import_post',
                'Import selesai dengan error validasi — tidak ada data disimpan.',
                filename=getattr(upload, 'name', None),
                total_rows=result.total_rows,
                error_count=len(result.errors),
            )

        return Response(
            serialize_liburan_import_result(result),
            status=status.HTTP_200_OK,
        )
