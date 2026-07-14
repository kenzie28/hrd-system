from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import is_admin_allowed
from .models import Karyawan
from .permissions import IsAdminAllowed
from .portal_views import _karyawan_for
from .serializers import PortalKaryawanSerializer, PortalLoginSerializer
from .services import create_portal_login


class AdminLoginView(APIView):
    """Login for the HRD admin-frontend. Only allowlisted Karyawan may enter."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PortalLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        karyawan_id = serializer.validated_data['karyawan_id']
        password = serializer.validated_data['password']

        user = authenticate(username=karyawan_id, password=password)
        if user is None:
            return Response(
                {'detail': 'ID karyawan atau kata sandi salah.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        karyawan = _karyawan_for(user)
        if karyawan is None:
            return Response(
                {'detail': 'Akun tidak terhubung ke data karyawan.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_admin_allowed(karyawan.karyawan_id):
            return Response(
                {'detail': 'Akun Anda tidak memiliki akses ke HRD Admin.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'karyawan': PortalKaryawanSerializer(karyawan).data,
            }
        )


class AdminMeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def get(self, request):
        karyawan = _karyawan_for(request.user)
        return Response(PortalKaryawanSerializer(karyawan).data)


class AdminResetPasswordView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def post(self, request, pk):
        karyawan = get_object_or_404(Karyawan, pk=pk)
        create_portal_login(karyawan)
        karyawan.refresh_from_db()
        return Response(PortalKaryawanSerializer(karyawan).data)
