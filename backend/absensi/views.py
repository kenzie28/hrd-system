from itertools import groupby

from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from karyawan.portal_views import _karyawan_for

from .models import Absensi
from .serializers import AbsensiConflictGroupSerializer, AbsensiSerializer


def _apply_common_filters(queryset, params):
    """Filter by ?karyawan_id=<id> and ?bulan=YYYY-MM."""
    karyawan_id = params.get('karyawan_id')
    if karyawan_id:
        queryset = queryset.filter(karyawan_id=karyawan_id)
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

    def create(self, request, *args, **kwargs):
        """Create Absensi, or return the existing row if all key fields match.

        Idempotent only when karyawan, lokasi, tanggal, jam_masuk, and durasi
        are identical. Different jam_masuk/durasi for the same day still create
        a new row (conflict resolution). Returns 201 if created, 200 if found.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        absensi, created = Absensi.objects.get_or_create(
            karyawan=data['karyawan'],
            lokasi=data['lokasi'],
            tanggal=data['tanggal'],
            jam_masuk=data['jam_masuk'],
            durasi=data['durasi'],
        )
        out = self.get_serializer(absensi)
        headers = self.get_success_headers(out.data) if created else {}
        return Response(
            out.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            headers=headers,
        )

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        """Group Absensi entries by (karyawan_id, tanggal); return only groups with >1 entry.

        Multiple clock-in/out entries for the same employee/day are never
        overwritten on create — they are stored side-by-side here until HRD
        resolves which one(s) should be kept. Exact duplicates (same lokasi,
        jam_masuk, and durasi) are skipped by create instead.
        """
        qs = Absensi.objects.select_related('karyawan', 'lokasi').order_by(
            'karyawan_id', 'tanggal', 'jam_masuk'
        )
        karyawan_id = request.query_params.get('karyawan_id')
        if karyawan_id:
            qs = qs.filter(karyawan_id=karyawan_id)

        groups = []
        for (karyawan_id, tanggal), entries in groupby(
            qs, key=lambda a: (a.karyawan_id, a.tanggal)
        ):
            entries = list(entries)
            if len(entries) > 1:
                groups.append(
                    {
                        'karyawan_id': karyawan_id,
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
