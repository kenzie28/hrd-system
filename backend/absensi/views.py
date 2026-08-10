from itertools import groupby

from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from karyawan.portal_views import _karyawan_for

from .models import Absensi
from .serializers import AbsensiConflictGroupSerializer, AbsensiSerializer


def _apply_common_filters(queryset, params):
    """Filter by ?karyawan=<id> and ?bulan=YYYY-MM."""
    karyawan = params.get('karyawan')
    if karyawan:
        queryset = queryset.filter(karyawan_id=karyawan)
    bulan = params.get('bulan')
    if bulan:
        year, month = map(int, bulan.split('-'))
        queryset = queryset.filter(tanggal__year=year, tanggal__month=month)
    return queryset


class AbsensiViewSet(viewsets.ModelViewSet):
    serializer_class = AbsensiSerializer

    def get_queryset(self):
        qs = Absensi.objects.select_related('karyawan', 'lokasi')
        return _apply_common_filters(qs, self.request.query_params)

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        """Group Absensi entries by (karyawan, tanggal); return only groups with >1 entry.

        Multiple clock-in/out entries for the same employee/day are never
        overwritten on create — they are stored side-by-side here until HRD
        resolves which one(s) should be kept.
        """
        qs = Absensi.objects.select_related('karyawan', 'lokasi').order_by(
            'karyawan_id', 'tanggal', 'jam_masuk'
        )
        karyawan = request.query_params.get('karyawan')
        if karyawan:
            qs = qs.filter(karyawan_id=karyawan)

        groups = []
        for (karyawan_id, tanggal), entries in groupby(
            qs, key=lambda a: (a.karyawan_id, a.tanggal)
        ):
            entries = list(entries)
            if len(entries) > 1:
                groups.append(
                    {
                        'karyawan': karyawan_id,
                        'karyawan_nama': entries[0].karyawan.nama,
                        'tanggal': tanggal,
                        'entries': entries,
                    }
                )

        return Response(AbsensiConflictGroupSerializer(groups, many=True).data)

    @action(detail=True, methods=['post'])
    def resolve_conflict(self, request, pk=None):
        """Keep this entry; delete sibling Absensi rows for the same (karyawan, tanggal)."""
        absensi = self.get_object()
        Absensi.objects.filter(
            karyawan=absensi.karyawan, tanggal=absensi.tanggal
        ).exclude(pk=absensi.pk).delete()
        return Response(AbsensiSerializer(absensi).data)


class PortalAbsensiViewSet(viewsets.ReadOnlyModelViewSet):
    """Employee-facing read-only view of their own absensi (portal-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = AbsensiSerializer

    def get_queryset(self):
        karyawan = _karyawan_for(self.request.user)
        if karyawan is None:
            return Absensi.objects.none()

        qs = Absensi.objects.filter(karyawan=karyawan).select_related('lokasi')
        bulan = self.request.query_params.get('bulan')
        if bulan:
            try:
                year, month = map(int, bulan.split('-'))
            except ValueError:
                return Absensi.objects.none()
            qs = qs.filter(tanggal__year=year, tanggal__month=month)
        return qs
