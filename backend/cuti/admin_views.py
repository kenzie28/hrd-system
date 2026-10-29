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

from .models import PermohonanCuti, StatusPermohonanCuti, TipeCuti
from .serializers import PermohonanCutiSerializer
from .services import (
    CutiImportError,
    CutiImportResult,
    approve_by_hrd,
    approve_cancellation_by_hrd,
    import_cuti_csv,
    serialize_cuti_import_result,
)


class AdminCutiImportView(APIView):
    """Import approved one-day annual or sick leave requests."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]
    tipe_cuti: str

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                serialize_cuti_import_result(
                    CutiImportResult(
                        errors=[CutiImportError(0, 'File CSV wajib diunggah.')]
                    )
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_cuti_csv(upload, self.tipe_cuti)
        except IntegrityError as exc:
            debug_exception(
                'cuti_import_post',
                'Import CSV cuti gagal: constraint database.',
                exc,
                tipe=self.tipe_cuti,
                filename=getattr(upload, 'name', None),
            )
            result = CutiImportResult(
                errors=[
                    CutiImportError(0, f'Gagal menyimpan data ke database: {exc}')
                ]
            )
        except Exception as exc:
            debug_exception(
                'cuti_import_post',
                'Import CSV cuti gagal dengan exception tak terduga.',
                exc,
                tipe=self.tipe_cuti,
                filename=getattr(upload, 'name', None),
            )
            result = CutiImportResult(
                errors=[CutiImportError(0, f'Import gagal: {exc}')]
            )

        return Response(
            serialize_cuti_import_result(result),
            status=status.HTTP_200_OK,
        )


class AdminCutiTahunanImportView(AdminCutiImportView):
    tipe_cuti = TipeCuti.TAHUNAN


class AdminCutiSakitImportView(AdminCutiImportView):
    tipe_cuti = TipeCuti.SAKIT


class AdminCutiViewSet(viewsets.ReadOnlyModelViewSet):
    """HRD approval queue for leave requests (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = PermohonanCutiSerializer

    def get_queryset(self):
        qs = PermohonanCuti.objects.select_related(
            'karyawan', 'supervisor', 'hrd_approver'
        )
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        else:
            qs = qs.filter(
                status__in=[
                    StatusPermohonanCuti.MENUNGGU_HRD,
                    StatusPermohonanCuti.MENUNGGU_PEMBATALAN_HRD,
                ]
            )
        return qs

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        permohonan = PermohonanCuti.objects.filter(pk=pk).first()
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status == StatusPermohonanCuti.MENUNGGU_HRD:
            hrd = _karyawan_for(request.user)
            created = approve_by_hrd(permohonan, hrd)
            data = PermohonanCutiSerializer(permohonan).data
            data['hari_dibuat'] = created
            return Response(data)
        if permohonan.status == StatusPermohonanCuti.MENUNGGU_PEMBATALAN_HRD:
            restored = approve_cancellation_by_hrd(permohonan)
            data = PermohonanCutiSerializer(permohonan).data
            data['hari_dihapus'] = restored
            return Response(data)
        return Response(
            {'detail': 'Permohonan tidak menunggu persetujuan HRD.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        permohonan = PermohonanCuti.objects.filter(pk=pk).first()
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status == StatusPermohonanCuti.MENUNGGU_HRD:
            permohonan.status = StatusPermohonanCuti.DITOLAK
            permohonan.save(update_fields=['status'])
            return Response(PermohonanCutiSerializer(permohonan).data)
        if permohonan.status == StatusPermohonanCuti.MENUNGGU_PEMBATALAN_HRD:
            permohonan.status = StatusPermohonanCuti.APPROVED
            permohonan.save(update_fields=['status'])
            return Response(PermohonanCutiSerializer(permohonan).data)
        return Response(
            {'detail': 'Permohonan tidak menunggu persetujuan HRD.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
