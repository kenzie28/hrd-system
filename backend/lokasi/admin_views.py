from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_error, debug_exception
from karyawan.permissions import IsAdminAllowed

from .models import Lokasi
from .serializers import LokasiSerializer
from .services import (
    LokasiImportError,
    LokasiImportResult,
    import_lokasi_csv,
    serialize_lokasi_import_result,
)


class AdminLokasiViewSet(viewsets.ModelViewSet):
    """HRD full CRUD for work locations (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = LokasiSerializer
    queryset = Lokasi.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        shift_count = instance.shifts.count()
        absensi_count = instance.absensi.count()
        if shift_count or absensi_count:
            parts = []
            if shift_count:
                parts.append(f'{shift_count} shift')
            if absensi_count:
                parts.append(f'{absensi_count} absensi')
            return Response(
                {
                    'detail': (
                        'Lokasi tidak dapat dihapus karena masih punya data terkait '
                        f'({", ".join(parts)}). Hapus data tersebut terlebih dahulu.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    'detail': (
                        'Lokasi tidak dapat dihapus karena masih punya data terkait. '
                        'Hapus data tersebut terlebih dahulu.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {
                    'detail': (
                        'Lokasi tidak dapat dihapus karena masih punya data terkait. '
                        'Hapus data tersebut terlebih dahulu.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminLokasiImportView(APIView):
    """CSV upload endpoint: columns id,nama."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            debug_error(
                'lokasi_import_post',
                'Request tanpa file CSV.',
                content_type=request.content_type,
                hint='Kirim multipart/form-data dengan field "file" berisi CSV.',
            )
            return Response(
                serialize_lokasi_import_result(
                    LokasiImportResult(
                        errors=[
                            LokasiImportError(0, 'File CSV wajib diunggah.'),
                        ],
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_lokasi_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'lokasi_import_post',
                'Import CSV gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = LokasiImportResult(
                errors=[
                    LokasiImportError(
                        0,
                        f'Gagal menyimpan data ke database: {exc}',
                    ),
                ],
            )
        except Exception as exc:
            debug_exception(
                'lokasi_import_post',
                'Import CSV gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
                size=getattr(upload, 'size', None),
            )
            result = LokasiImportResult(
                errors=[
                    LokasiImportError(
                        0,
                        f'Import gagal: {exc}',
                    ),
                ],
            )

        if not result.ok:
            debug_error(
                'lokasi_import_post',
                'Import selesai dengan error validasi — tidak ada data disimpan.',
                filename=getattr(upload, 'name', None),
                total_rows=result.total_rows,
                error_count=len(result.errors),
            )

        return Response(
            serialize_lokasi_import_result(result),
            status=status.HTTP_200_OK,
        )
