from rest_framework import viewsets

from .models import Lokasi
from .serializers import LokasiSerializer


class LokasiViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lokasi.objects.all()
    serializer_class = LokasiSerializer
