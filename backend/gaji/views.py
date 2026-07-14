from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from karyawan.serializers import PortalKaryawanSerializer
from karyawan.portal_views import _karyawan_for

from .models import GajiTemp
from .serializers import GajiTempSerializer


class PortalGajiView(APIView):
    """Employee-facing salary breakdown for a given month (?bulan=YYYY-MM)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        karyawan = _karyawan_for(request.user)
        if karyawan is None:
            return Response(
                {'detail': 'Akun tidak terhubung ke data karyawan.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        bulan = request.query_params.get('bulan')
        gaji = None
        if bulan:
            try:
                year, month = map(int, bulan.split('-'))
            except ValueError:
                year = month = None
            if year and month:
                gaji = GajiTemp.objects.filter(
                    karyawan=karyawan, periode__year=year, periode__month=month
                ).first()

        return Response(
            {
                'karyawan': PortalKaryawanSerializer(karyawan).data,
                'bulan': bulan,
                'gaji': GajiTempSerializer(gaji).data if gaji else None,
            }
        )
