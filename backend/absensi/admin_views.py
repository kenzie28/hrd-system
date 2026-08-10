from django.db import IntegrityError
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_error, debug_exception
from karyawan.permissions import IsAdminAllowed

from .services import (
    AbsensiImportError,
    AbsensiImportResult,
    import_absensi_csv,
    serialize_absensi_import_result,
)


class AdminAbsensiImportView(APIView):
    """CSV upload endpoint: columns karyawan_id,lokasi_kerja,tanggal,jam_masuk,jam_keluar."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            debug_error(
                'absensi_import_post',
                'Request tanpa file CSV.',
                content_type=request.content_type,
                hint='Kirim multipart/form-data dengan field "file" berisi CSV.',
            )
            return Response(
                serialize_absensi_import_result(
                    AbsensiImportResult(
                        errors=[
                            AbsensiImportError(0, 'File CSV wajib diunggah.'),
                        ],
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_absensi_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'absensi_import_post',
                'Import CSV gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = AbsensiImportResult(
                errors=[
                    AbsensiImportError(
                        0,
                        f'Gagal menyimpan data ke database: {exc}',
                    ),
                ],
            )
        except Exception as exc:
            debug_exception(
                'absensi_import_post',
                'Import CSV gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
                size=getattr(upload, 'size', None),
            )
            result = AbsensiImportResult(
                errors=[
                    AbsensiImportError(
                        0,
                        f'Import gagal: {exc}',
                    ),
                ],
            )

        if not result.ok:
            debug_error(
                'absensi_import_post',
                'Import selesai dengan error validasi — tidak ada data disimpan.',
                filename=getattr(upload, 'name', None),
                total_rows=result.total_rows,
                error_count=len(result.errors),
            )

        return Response(
            serialize_absensi_import_result(result),
            status=status.HTTP_200_OK,
        )
