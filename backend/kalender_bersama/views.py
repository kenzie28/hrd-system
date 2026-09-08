from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from karyawan.portal_views import _karyawan_for

from .serializers import (
    KalenderHariSerializer,
    KaryawanSearchSerializer,
    LanggananCreateSerializer,
    LanggananSerializer,
    NotifikasiSerializer,
)
from .services import (
    ServiceError,
    calendar_days,
    dismiss_notification,
    list_langganan,
    parse_date_range,
    search_karyawan,
    subscribe,
    subscribed_ids,
    unsubscribe,
    upcoming_cuti,
)


class PortalKalenderBersamaView(APIView):
    """Employee-facing shared leave calendar (portal-frontend)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def karyawan(self, request):
        return _karyawan_for(request.user)

    def require_karyawan(self, request):
        karyawan = self.karyawan(request)
        if karyawan is None:
            return None, Response(
                {'detail': 'Akun tidak terhubung ke data karyawan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return karyawan, None


def _service_error_response(exc: ServiceError):
    return Response({'detail': exc.detail}, status=exc.status_code)


class LanggananListCreateView(PortalKalenderBersamaView):
    def get(self, request):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        qs = list_langganan(karyawan)
        return Response(LanggananSerializer(qs, many=True).data)

    def post(self, request):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        serializer = LanggananCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            langganan = subscribe(karyawan, serializer.validated_data['karyawan_id'])
        except ServiceError as exc:
            return _service_error_response(exc)
        return Response(
            LanggananSerializer(langganan).data,
            status=status.HTTP_201_CREATED,
        )


class LanggananDestroyView(PortalKalenderBersamaView):
    def delete(self, request, karyawan_id):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        try:
            unsubscribe(karyawan, karyawan_id)
        except ServiceError as exc:
            return _service_error_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class KaryawanSearchView(PortalKalenderBersamaView):
    def get(self, request):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        qs = search_karyawan(karyawan, request.query_params.get('q'))
        return Response(
            KaryawanSearchSerializer(
                qs,
                many=True,
                context={'subscribed_ids': set(subscribed_ids(karyawan))},
            ).data
        )


class NotifikasiListView(PortalKalenderBersamaView):
    def get(self, request):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        qs = upcoming_cuti(karyawan)
        return Response(NotifikasiSerializer(qs, many=True).data)


class NotifikasiDismissView(PortalKalenderBersamaView):
    def post(self, request, pk):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        try:
            dismiss_notification(karyawan, pk)
        except ServiceError as exc:
            return _service_error_response(exc)
        return Response({'ok': True})


class KalenderView(PortalKalenderBersamaView):
    def get(self, request):
        karyawan, error = self.require_karyawan(request)
        if error is not None:
            return error
        try:
            dari, sampai = parse_date_range(
                request.query_params.get('dari'),
                request.query_params.get('sampai'),
            )
        except ServiceError as exc:
            return _service_error_response(exc)
        qs = calendar_days(karyawan, dari, sampai)
        return Response(KalenderHariSerializer(qs, many=True).data)
