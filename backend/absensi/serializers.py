from rest_framework import serializers

from .models import Absensi


class AbsensiSerializer(serializers.ModelSerializer):
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    lokasi_nama = serializers.CharField(source='lokasi.nama', read_only=True)
    jam_keluar = serializers.TimeField(read_only=True)
    keluar_hari_offset = serializers.ReadOnlyField()

    class Meta:
        model = Absensi
        fields = [
            'id', 'karyawan', 'karyawan_nama', 'lokasi', 'lokasi_nama',
            'tanggal', 'jam_masuk', 'durasi', 'jam_keluar', 'keluar_hari_offset',
        ]


class AbsensiConflictGroupSerializer(serializers.Serializer):
    karyawan = serializers.IntegerField()
    karyawan_nama = serializers.CharField()
    tanggal = serializers.DateField()
    entries = AbsensiSerializer(many=True)
