from datetime import datetime

from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_exception
from karyawan.models import Karyawan
from karyawan.permissions import IsAdminAllowed
from karyawan.portal_views import _karyawan_for

from .models import PermohonanLembur, StatusPermohonanLembur
from .serializers import PermohonanLemburSerializer
from .services import (
    LemburImportError,
    LemburImportResult,
    approve_by_hrd,
    clear_approved_lembur,
    ensure_approved_lembur,
    import_lembur_csv,
    serialize_lembur_import_result,
)


def _lembur_day(data):
    """Return ``(karyawan, tanggal, error_response)`` for an add/remove body."""
    if not isinstance(data, dict):
        return None, None, Response(
            {'detail': 'Body harus berupa objek.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    karyawan_id = data.get('karyawan_id')
    if not isinstance(karyawan_id, str) or not karyawan_id.strip():
        return None, None, Response(
            {'karyawan_id': 'karyawan_id wajib diisi.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    karyawan = Karyawan.objects.filter(pk=karyawan_id.strip()).first()
    if karyawan is None:
        return None, None, Response(
            {'karyawan_id': 'Karyawan tidak ditemukan.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tanggal_raw = data.get('tanggal')
    tanggal = None
    if isinstance(tanggal_raw, str):
        try:
            tanggal = datetime.strptime(tanggal_raw.strip(), '%Y-%m-%d').date()
        except ValueError:
            tanggal = None
    if tanggal is None:
        return None, None, Response(
            {'tanggal': 'tanggal harus format yyyy-mm-dd.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return karyawan, tanggal, None


class AdminLemburImportView(APIView):
    """Import approved one-day overtime requests."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                serialize_lembur_import_result(
                    LemburImportResult(
                        errors=[LemburImportError(0, 'File CSV wajib diunggah.')]
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_lembur_csv(upload)
        except IntegrityError as exc:
            debug_exception(
                'lembur_import_post',
                'Import CSV lembur gagal: constraint database.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = LemburImportResult(
                errors=[
                    LemburImportError(0, f'Gagal menyimpan data ke database: {exc}')
                ]
            )
        except Exception as exc:
            debug_exception(
                'lembur_import_post',
                'Import CSV lembur gagal dengan exception tak terduga.',
                exc,
                filename=getattr(upload, 'name', None),
            )
            result = LemburImportResult(
                errors=[LemburImportError(0, f'Import gagal: {exc}')]
            )

        return Response(
            serialize_lembur_import_result(result),
            status=status.HTTP_200_OK,
        )


class AdminLemburViewSet(viewsets.ReadOnlyModelViewSet):
    """HRD approval queue for overtime requests (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = PermohonanLemburSerializer

    def get_queryset(self):
        qs = PermohonanLembur.objects.select_related(
            'karyawan', 'supervisor', 'hrd_approver'
        )
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        else:
            qs = qs.filter(status=StatusPermohonanLembur.MENUNGGU_HRD)

        karyawan_id = self.request.query_params.get('karyawan_id')
        if karyawan_id:
            qs = qs.filter(karyawan_id=karyawan_id)
        bulan = self.request.query_params.get('bulan')
        if bulan:
            year, month = map(int, bulan.split('-'))
            qs = qs.filter(tanggal__year=year, tanggal__month=month)
        return qs

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Create an approved overtime request for one employee and date."""
        karyawan, tanggal, error = _lembur_day(request.data)
        if error is not None:
            return error
        permohonan, created = ensure_approved_lembur(karyawan, tanggal)
        return Response(
            PermohonanLemburSerializer(permohonan).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'])
    def remove(self, request):
        """Delete approved overtime for one employee and date."""
        karyawan, tanggal, error = _lembur_day(request.data)
        if error is not None:
            return error
        clear_approved_lembur(karyawan, tanggal)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        permohonan = PermohonanLembur.objects.filter(pk=pk).first()
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status != StatusPermohonanLembur.MENUNGGU_HRD:
            return Response(
                {'detail': 'Permohonan tidak menunggu persetujuan HRD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        hrd = _karyawan_for(request.user)
        approve_by_hrd(permohonan, hrd)
        return Response(PermohonanLemburSerializer(permohonan).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        permohonan = PermohonanLembur.objects.filter(pk=pk).first()
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status != StatusPermohonanLembur.MENUNGGU_HRD:
            return Response(
                {'detail': 'Permohonan tidak menunggu persetujuan HRD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        permohonan.status = StatusPermohonanLembur.DITOLAK
        permohonan.save(update_fields=['status'])
        return Response(PermohonanLemburSerializer(permohonan).data)
