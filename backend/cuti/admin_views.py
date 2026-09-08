from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from karyawan.permissions import IsAdminAllowed
from karyawan.portal_views import _karyawan_for

from .models import PermohonanCuti, StatusPermohonanCuti
from .serializers import PermohonanCutiSerializer
from .services import approve_by_hrd, approve_cancellation_by_hrd


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
