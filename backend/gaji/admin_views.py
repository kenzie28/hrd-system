from dataclasses import asdict

from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminAllowed

from .models import GajiTemp
from .serializers import GajiTempSerializer
from .services import import_gaji_csv


def _apply_common_filters(queryset, params):
    """Filter by ?karyawan=<id> and ?bulan=YYYY-MM."""
    karyawan = params.get('karyawan')
    if karyawan:
        queryset = queryset.filter(karyawan_id=karyawan)
    bulan = params.get('bulan')
    if bulan:
        year, month = map(int, bulan.split('-'))
        queryset = queryset.filter(periode__year=year, periode__month=month)
    return queryset


class AdminGajiViewSet(viewsets.ReadOnlyModelViewSet):
    """HRD review list of imported payroll rows (admin-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    serializer_class = GajiTempSerializer

    def get_queryset(self):
        qs = GajiTemp.objects.select_related('karyawan')
        return _apply_common_filters(qs, self.request.query_params)


class AdminGajiImportView(APIView):
    """CSV upload endpoint for HRD to import a month's payroll data."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                {'detail': 'File CSV wajib diunggah.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upsert_karyawan = str(request.data.get('upsert_karyawan', 'true')).lower() in (
            'true',
            '1',
            'yes',
        )

        result = import_gaji_csv(upload, upsert_karyawan=upsert_karyawan)
        data = asdict(result)
        data['ok'] = result.ok
        return Response(data, status=status.HTTP_200_OK)
