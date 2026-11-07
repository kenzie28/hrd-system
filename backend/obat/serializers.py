from rest_framework import serializers

from .models import TunjanganObat


class TunjanganObatSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.PrimaryKeyRelatedField(
        source='karyawan', read_only=True
    )
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)

    class Meta:
        model = TunjanganObat
        fields = ['id', 'karyawan_id', 'karyawan_nama', 'nominal', 'bulan']
