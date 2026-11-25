from rest_framework import serializers

from .models import Dinas


class DinasSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.PrimaryKeyRelatedField(source='karyawan', read_only=True)
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)

    class Meta:
        model = Dinas
        fields = ['id', 'karyawan_id', 'karyawan_nama', 'tanggal']
