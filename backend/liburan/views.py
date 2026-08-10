from rest_framework import viewsets

from .models import Liburan
from .serializers import LiburanSerializer


class LiburanViewSet(viewsets.ReadOnlyModelViewSet):
    """Open read-only list of holidays (backward compatible)."""

    queryset = Liburan.objects.all()
    serializer_class = LiburanSerializer
