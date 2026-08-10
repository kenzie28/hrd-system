from rest_framework import viewsets

from .models import Shift
from .serializers import ShiftSerializer


class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer

    def get_queryset(self):
        qs = Shift.objects.select_related('lokasi_kerja')
        lokasi_kerja = self.request.query_params.get('lokasi_kerja')
        if lokasi_kerja:
            qs = qs.filter(lokasi_kerja_id=lokasi_kerja)
        return qs
