from datetime import date, timedelta

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Absensi, Cuti, Jadwal, Liburan, RekapKehadiran, Shift
from .serializers import (
    AbsensiSerializer,
    CutiSerializer,
    JadwalBulkSerializer,
    JadwalSerializer,
    LiburanSerializer,
    RekapKehadiranSerializer,
    RekapProcessSerializer,
    ShiftSerializer,
)
from .services import process_rekap


def _apply_common_filters(queryset, params, karyawan_field='karyawan_id', tanggal_field='tanggal'):
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


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer


class JadwalViewSet(viewsets.ModelViewSet):
    serializer_class = JadwalSerializer

    def get_queryset(self):
        qs = Jadwal.objects.select_related('karyawan', 'shift')
        return _apply_common_filters(qs, self.request.query_params)

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        serializer = JadwalBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        existing = {
            (k, t)
            for k, t in Jadwal.objects.filter(
                karyawan__in=data['karyawan_ids'],
                tanggal__range=(data['tanggal_mulai'], data['tanggal_selesai']),
            ).values_list('karyawan_id', 'tanggal')
        }

        to_create = []
        current = data['tanggal_mulai']
        while current <= data['tanggal_selesai']:
            for karyawan in data['karyawan_ids']:
                if (karyawan.id, current) not in existing:
                    to_create.append(
                        Jadwal(karyawan=karyawan, shift=data['shift_id'], tanggal=current)
                    )
            current += timedelta(days=1)

        Jadwal.objects.bulk_create(to_create)
        return Response(
            {'created': len(to_create), 'skipped_existing': len(existing)},
            status=status.HTTP_201_CREATED,
        )


class AbsensiViewSet(viewsets.ModelViewSet):
    serializer_class = AbsensiSerializer

    def get_queryset(self):
        qs = Absensi.objects.select_related('karyawan', 'lokasi')
        return _apply_common_filters(qs, self.request.query_params)


class CutiViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CutiSerializer

    def get_queryset(self):
        qs = Cuti.objects.select_related(
            'permohonan__karyawan', 'permohonan__supervisor'
        )
        return _apply_common_filters(
            qs,
            self.request.query_params,
            karyawan_field='permohonan__karyawan_id',
        )


class RekapKehadiranViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RekapKehadiranSerializer

    def get_queryset(self):
        qs = RekapKehadiran.objects.select_related(
            'jadwal__karyawan', 'jadwal__shift', 'absensi__lokasi',
            'absensi__karyawan', 'cuti__permohonan__karyawan',
        )
        return _apply_common_filters(
            qs,
            self.request.query_params,
            karyawan_field='jadwal__karyawan_id',
            tanggal_field='jadwal__tanggal',
        )

    @action(detail=False, methods=['post'])
    def process(self, request):
        serializer = RekapProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        count = process_rekap(data['tanggal_mulai'], data['tanggal_selesai'])
        return Response({'processed': count})


class LiburanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Liburan.objects.all()
    serializer_class = LiburanSerializer
