from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsAdminAllowed
from core.portal_views import _karyawan_for

from .models import PermohonanCuti, StatusPermohonanCuti
from .serializers import PermohonanCutiSerializer
from .services import approve_by_hrd


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
            qs = qs.filter(status=StatusPermohonanCuti.MENUNGGU_HRD)
        return qs

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        permohonan = PermohonanCuti.objects.filter(pk=pk).first()
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status != StatusPermohonanCuti.MENUNGGU_HRD:
            return Response(
                {'detail': 'Permohonan tidak menunggu persetujuan HRD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        hrd = _karyawan_for(request.user)
        created = approve_by_hrd(permohonan, hrd)
        data = PermohonanCutiSerializer(permohonan).data
        data['hari_dibuat'] = created
        return Response(data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        permohonan = PermohonanCuti.objects.filter(pk=pk).first()
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status != StatusPermohonanCuti.MENUNGGU_HRD:
            return Response(
                {'detail': 'Permohonan tidak menunggu persetujuan HRD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        permohonan.status = StatusPermohonanCuti.DITOLAK
        permohonan.save(update_fields=['status'])
        return Response(PermohonanCutiSerializer(permohonan).data)
