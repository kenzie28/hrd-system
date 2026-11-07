from rest_framework import serializers

from .models import Koreksi


class KoreksiSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.PrimaryKeyRelatedField(
        source='karyawan', read_only=True
    )
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    tipe = serializers.CharField(source='get_tipe_display', read_only=True)

    class Meta:
        model = Koreksi
        fields = ['id', 'karyawan_id', 'karyawan_nama', 'tipe', 'nominal', 'bulan']
