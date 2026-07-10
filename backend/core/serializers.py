from rest_framework import serializers

from .models import Karyawan, Lokasi


class LokasiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lokasi
        fields = ['id', 'nama']


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
            'default_shift',
        ]
