from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Karyawan
from .portal_serializers import (
    ChangePasswordSerializer,
    PortalKaryawanSerializer,
    PortalLoginSerializer,
)


def _karyawan_for(user):
    return Karyawan.objects.filter(user=user).first()


class PortalLoginView(APIView):
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

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'must_change_password': karyawan.must_change_password,
                'karyawan': PortalKaryawanSerializer(karyawan).data,
            }
        )


class PortalMeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        karyawan = _karyawan_for(request.user)
        if karyawan is None:
            return Response(
                {'detail': 'Akun tidak terhubung ke data karyawan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(PortalKaryawanSerializer(karyawan).data)


class PortalChangePasswordView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['new_password']

        user = request.user
        user.set_password(new_password)
        user.save()

        karyawan = _karyawan_for(user)
        if karyawan is not None:
            karyawan.must_change_password = False
            karyawan.save(update_fields=['must_change_password'])

        # Rotate the token so old sessions are invalidated after a password change.
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response({'token': token.key, 'must_change_password': False})
