from rest_framework import serializers

from .models import Karyawan


class PortalKaryawanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = ['id', 'karyawan_id', 'nama', 'level', 'must_change_password']


class PortalLoginSerializer(serializers.Serializer):
    karyawan_id = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(style={'input_type': 'password'})
