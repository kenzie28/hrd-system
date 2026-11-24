from rest_framework import serializers

from .models import Karyawan


class KaryawanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = [
            'karyawan_id',
            'nama',
            'lokasi_kerja',
            'jabatan',
            'wilayah',
            'level',
            'cuti_tahunan',
            'status_k_tk',
            'akumulasi_lembur',
        ]


class KaryawanWriteSerializer(serializers.ModelSerializer):
    """Create/update payload for admin Master Karyawan."""

    class Meta:
        model = Karyawan
        fields = [
            'karyawan_id',
            'nama',
            'lokasi_kerja',
            'jabatan',
            'wilayah',
            'level',
            'cuti_tahunan',
            'status_k_tk',
        ]

    def update(self, instance, validated_data):
        validated_data.pop('karyawan_id', None)
        return super().update(instance, validated_data)


class PortalKaryawanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = [
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
