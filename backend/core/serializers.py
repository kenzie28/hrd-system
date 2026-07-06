from rest_framework import serializers

from .models import Karyawan, Lokasi


class LokasiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lokasi
        fields = ['id', 'nama']


class KaryawanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = ['id', 'nama', 'default_shift']
