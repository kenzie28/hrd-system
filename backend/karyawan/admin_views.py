from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_error, debug_exception

from .access import is_admin_allowed
from .login import authenticate_karyawan_credentials
from .models import Karyawan
from .permissions import IsAdminAllowed
from .portal_views import _karyawan_for
from .serializers import (
    KaryawanWriteSerializer,
    PortalKaryawanSerializer,
    PortalLoginSerializer,
)
from .services import (
    KaryawanImportError,
    KaryawanImportResult,
    create_portal_login,
    import_karyawan_csv,
    serialize_karyawan_import_result,
)


class AdminLoginView(APIView):
    """Login for the HRD admin-frontend. Only allowlisted Karyawan may enter."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PortalLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        karyawan_id = serializer.validated_data['karyawan_id']
        password = serializer.validated_data['password']

        user, auth_error = authenticate_karyawan_credentials(karyawan_id, password)
        if auth_error is not None:
            return auth_error

        karyawan = _karyawan_for(user)
        if karyawan is None:
            return Response(
                {'detail': 'Akun tidak terhubung ke data karyawan.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_admin_allowed(karyawan.karyawan_id):
            return Response(
                {'detail': 'Akun Anda tidak memiliki akses ke HRD Admin.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'karyawan': PortalKaryawanSerializer(karyawan).data,
            }
        )


class AdminMeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def get(self, request):
        karyawan = _karyawan_for(request.user)
        return Response(PortalKaryawanSerializer(karyawan).data)


class AdminResetPasswordView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def post(self, request, pk):
        karyawan = get_object_or_404(Karyawan, pk=pk)
        create_portal_login(karyawan)
        karyawan.refresh_from_db()
        return Response(PortalKaryawanSerializer(karyawan).data)


class AdminKaryawanCreateView(APIView):
    """Create a single Karyawan from the admin Master Karyawan form."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def post(self, request):
        serializer = KaryawanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        karyawan = serializer.save()
        return Response(
            KaryawanWriteSerializer(karyawan).data,
            status=status.HTTP_201_CREATED,
        )


class AdminKaryawanDetailView(APIView):
    """Update or delete a single Karyawan from the admin Master Karyawan table."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def patch(self, request, pk):
        karyawan = get_object_or_404(Karyawan, pk=pk)
        serializer = KaryawanWriteSerializer(karyawan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(KaryawanWriteSerializer(karyawan).data)

    def delete(self, request, pk):
        karyawan = get_object_or_404(Karyawan, pk=pk)

        # Never allow an admin to delete their own login account.
        if karyawan.user_id and karyawan.user_id == request.user.id:
            return Response(
                {'detail': 'Tidak dapat menghapus akun yang sedang Anda gunakan.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.username == karyawan.karyawan_id:
            return Response(
                {'detail': 'Tidak dapat menghapus akun yang sedang Anda gunakan.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        portal_user = karyawan.user
        try:
            with transaction.atomic():
                karyawan.delete()
                if portal_user is not None:
                    portal_user.delete()
        except ProtectedError:
            return Response(
                {
                    'detail': (
                        'Karyawan tidak dapat dihapus karena masih punya data terkait '
                        '(cuti, lembur, atau gaji). Hapus data tersebut terlebih dahulu.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminKaryawanImportView(APIView):
    """CSV upload: karyawan_id, nama, level (+ optional jabatan, wilayah, lokasi_kerja)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            debug_error(
                'karyawan_import_post',
                'Request tanpa file CSV.',
                content_type=request.content_type,
                hint='Kirim multipart/form-data dengan field "file" berisi CSV.',
            )
            return Response(
                serialize_karyawan_import_result(
                    KaryawanImportResult(
                        errors=[
                            KaryawanImportError(0, 'File CSV wajib diunggah.'),
                        ],
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_karyawan_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'karyawan_import_post',
                'Import CSV gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = KaryawanImportResult(
                errors=[
                    KaryawanImportError(
                        0,
                        f'Gagal menyimpan data ke database: {exc}',
                    ),
                ],
            )
        except Exception as exc:
            debug_exception(
                'karyawan_import_post',
                'Import CSV gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
                size=getattr(upload, 'size', None),
            )
            result = KaryawanImportResult(
                errors=[
                    KaryawanImportError(
                        0,
                        f'Import gagal: {exc}',
                    ),
                ],
            )

        if not result.ok:
            debug_error(
                'karyawan_import_post',
                'Import selesai dengan error validasi — tidak ada data disimpan.',
                filename=getattr(upload, 'name', None),
                total_rows=result.total_rows,
                error_count=len(result.errors),
            )

        return Response(
            serialize_karyawan_import_result(result),
            status=status.HTTP_200_OK,
        )
