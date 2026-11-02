from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.debug_log import debug_exception
from karyawan.permissions import IsAdminAllowed
from karyawan.portal_views import _karyawan_for

from .models import PermohonanLembur, StatusPermohonanLembur
from .serializers import PermohonanLemburSerializer
from .services import (
    LemburImportError,
    LemburImportResult,
    approve_by_hrd,
    import_lembur_csv,
    serialize_lembur_import_result,
)


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
