from rest_framework import viewsets

from .models import Karyawan, Lokasi
from .serializers import KaryawanSerializer, LokasiSerializer


class KaryawanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Karyawan.objects.all()
    serializer_class = KaryawanSerializer


class LokasiViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lokasi.objects.all()
    serializer_class = LokasiSerializer
