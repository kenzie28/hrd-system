from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

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

    def destroy(self, request, *args, **kwargs):
        """Delete a shift. Processed Kehadiran keeps the day and drops the shift link."""
        instance = self.get_object()
        try:
            with transaction.atomic():
                instance.kehadiran.all().update(shift=None)
                instance.delete()
        except (ProtectedError, IntegrityError):
            return Response(
                {'detail': 'Shift tidak dapat dihapus karena masih punya data terkait.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
