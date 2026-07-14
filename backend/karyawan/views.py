from rest_framework import viewsets

from .models import Karyawan
from .serializers import KaryawanSerializer


class KaryawanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Karyawan.objects.all()
    serializer_class = KaryawanSerializer
