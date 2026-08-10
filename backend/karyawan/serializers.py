from rest_framework import serializers

from .models import Karyawan


class KaryawanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = [
            'id',
            'karyawan_id',
            'nama',
            'lokasi_kerja',
            'jabatan',
            'wilayah',
            'level',
            'cuti_tahunan',
        ]


class KaryawanWriteSerializer(serializers.ModelSerializer):
    """Create/update payload for admin Master Karyawan."""

    class Meta:
        model = Karyawan
        fields = [
            'id',
            'karyawan_id',
            'nama',
            'lokasi_kerja',
            'jabatan',
            'wilayah',
            'level',
            'cuti_tahunan',
        ]
        read_only_fields = ['id']


class PortalKaryawanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = [
            'id',
            'karyawan_id',
            'nama',
            'level',
            'must_change_password',
            'cuti_tahunan',
        ]


class PortalLoginSerializer(serializers.Serializer):
    karyawan_id = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(style={'input_type': 'password'})
