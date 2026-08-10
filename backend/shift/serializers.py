from rest_framework import serializers

from .models import Shift


class ShiftSerializer(serializers.ModelSerializer):
    lokasi_kerja_nama = serializers.CharField(source='lokasi_kerja.nama', read_only=True)
    hari_display = serializers.CharField(source='get_hari_display', read_only=True)

    class Meta:
        model = Shift
        fields = [
            'id', 'lokasi_kerja', 'lokasi_kerja_nama', 'hari', 'hari_display',
            'jam_masuk', 'jam_keluar',
        ]
