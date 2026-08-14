from rest_framework import serializers

from karyawan.models import Karyawan

from .models import Absensi


class AbsensiSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.PrimaryKeyRelatedField(
        source='karyawan', queryset=Karyawan.objects.all()
    )
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    lokasi_nama = serializers.CharField(source='lokasi.nama', read_only=True)
    jam_keluar = serializers.TimeField(read_only=True)
    keluar_hari_offset = serializers.ReadOnlyField()

    class Meta:
        model = Absensi
        fields = [
            'id', 'karyawan_id', 'karyawan_nama', 'lokasi', 'lokasi_nama',
            'tanggal', 'jam_masuk', 'durasi', 'jam_keluar', 'keluar_hari_offset',
        ]
        # Uniqueness is enforced in the DB; create is idempotent in the view
        # (get_or_create) and must not fail validation on exact duplicates.
        validators = []


class AbsensiConflictGroupSerializer(serializers.Serializer):
    karyawan_id = serializers.CharField()
    karyawan_nama = serializers.CharField()
    tanggal = serializers.DateField()
    entries = AbsensiSerializer(many=True)
