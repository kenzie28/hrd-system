from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Karyawan
from core.portal_views import _karyawan_for

from .models import Cuti, PermohonanCuti, StatusPermohonanCuti, ACTIVE_STATUSES
from .policy import eligible_supervisor_levels
from .serializers import (
    CutiSerializer,
    PermohonanCutiCreateSerializer,
    PermohonanCutiSerializer,
    SupervisorOptionSerializer,
)


def _apply_common_filters(queryset, params, karyawan_field='permohonan__karyawan_id', tanggal_field='tanggal'):
    """Filter by ?karyawan=<id> and ?bulan=YYYY-MM."""
    karyawan = params.get('karyawan')
    if karyawan:
        queryset = queryset.filter(**{karyawan_field: karyawan})
    bulan = params.get('bulan')
    if bulan:
        year, month = map(int, bulan.split('-'))
        queryset = queryset.filter(
            **{f'{tanggal_field}__year': year, f'{tanggal_field}__month': month}
        )
    return queryset


class CutiViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only per-day leave ledger (consumed by the admin attendance views)."""

    serializer_class = CutiSerializer

    def get_queryset(self):
        qs = Cuti.objects.select_related(
            'permohonan__karyawan', 'permohonan__supervisor'
        )
        return _apply_common_filters(qs, self.request.query_params)


class PortalCutiViewSet(viewsets.ModelViewSet):
    """Employee-facing leave request workflow (portal-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']

    def _karyawan(self):
        karyawan = _karyawan_for(self.request.user)
        if karyawan is None:
            return None
        return karyawan

    def get_serializer_class(self):
        if self.action == 'create':
            return PermohonanCutiCreateSerializer
        return PermohonanCutiSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['karyawan'] = self._karyawan()
        return ctx

    def get_queryset(self):
        karyawan = self._karyawan()
        if karyawan is None:
            return PermohonanCuti.objects.none()
        return PermohonanCuti.objects.filter(karyawan=karyawan).select_related(
            'karyawan', 'supervisor', 'hrd_approver'
        )

    def create(self, request, *args, **kwargs):
        karyawan = self._karyawan()
        if karyawan is None:
            return Response(
                {'detail': 'Akun tidak terhubung ke data karyawan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permohonan = serializer.save()
        return Response(
            PermohonanCutiSerializer(permohonan).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        permohonan = self.get_object()
        if permohonan.status not in ACTIVE_STATUSES:
            return Response(
                {'detail': 'Permohonan ini tidak dapat dibatalkan.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        permohonan.status = StatusPermohonanCuti.DIBATALKAN
        permohonan.save(update_fields=['status'])
        return Response(PermohonanCutiSerializer(permohonan).data)

    @action(detail=False, methods=['get'])
    def supervisors(self, request):
        karyawan = self._karyawan()
        if karyawan is None:
            return Response([])
        levels = eligible_supervisor_levels(karyawan.level)
        qs = (
            Karyawan.objects.filter(level__in=levels)
            .exclude(id=karyawan.id)
            .order_by('nama')
        )
        return Response(SupervisorOptionSerializer(qs, many=True).data)

    # ---- Supervisor approval (level >= MIN_SUPERVISOR_LEVEL) ----

    @action(detail=False, methods=['get'])
    def approvals(self, request):
        karyawan = self._karyawan()
        if karyawan is None:
            return Response([])
        qs = (
            PermohonanCuti.objects.filter(
                supervisor=karyawan,
                status=StatusPermohonanCuti.MENUNGGU_SUPERVISOR,
            )
            .select_related('karyawan', 'supervisor', 'hrd_approver')
        )
        return Response(PermohonanCutiSerializer(qs, many=True).data)

    def _get_supervised(self, pk):
        karyawan = self._karyawan()
        if karyawan is None:
            return None, None
        permohonan = PermohonanCuti.objects.filter(
            pk=pk, supervisor=karyawan
        ).first()
        return karyawan, permohonan

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        _, permohonan = self._get_supervised(pk)
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status != StatusPermohonanCuti.MENUNGGU_SUPERVISOR:
            return Response(
                {'detail': 'Permohonan tidak menunggu persetujuan supervisor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        permohonan.status = StatusPermohonanCuti.MENUNGGU_HRD
        permohonan.save(update_fields=['status'])
        return Response(PermohonanCutiSerializer(permohonan).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        _, permohonan = self._get_supervised(pk)
        if permohonan is None:
            return Response(
                {'detail': 'Permohonan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if permohonan.status != StatusPermohonanCuti.MENUNGGU_SUPERVISOR:
            return Response(
                {'detail': 'Permohonan tidak menunggu persetujuan supervisor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        permohonan.status = StatusPermohonanCuti.DITOLAK
        permohonan.save(update_fields=['status'])
        return Response(PermohonanCutiSerializer(permohonan).data)
