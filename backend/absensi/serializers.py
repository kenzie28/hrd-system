from rest_framework import serializers

from karyawan.models import Karyawan

from .models import Absensi, CatatanRekapAbsensi, Kehadiran, RekapAbsensi


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


class CatatanRekapAbsensiSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatatanRekapAbsensi
        fields = ['id', 'tanggal', 'pesan']


class RekapAbsensiSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.CharField(read_only=True)
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    catatan = CatatanRekapAbsensiSerializer(many=True, read_only=True)

    class Meta:
        model = RekapAbsensi
        fields = [
            'id',
            'month',
            'karyawan_id',
            'karyawan_nama',
            'hari_hadir',
            'hari_telat',
            'hari_alpa',
            'hari_keluar_cepat',
            'total_menit_telat',
            'total_menit_lembur',
            'catatan',
        ]


class KehadiranSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.CharField(read_only=True)
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shift_jam_masuk = serializers.SerializerMethodField()
    shift_jam_keluar = serializers.SerializerMethodField()

    def get_shift_jam_masuk(self, obj):
        return obj.shift.jam_masuk.isoformat() if obj.shift_id else None

    def get_shift_jam_keluar(self, obj):
        return obj.shift.jam_keluar.isoformat() if obj.shift_id else None

    class Meta:
        model = Kehadiran
        fields = [
            'id',
            'tanggal',
            'karyawan_id',
            'karyawan_nama',
            'status',
            'status_display',
            'shift_jam_masuk',
            'shift_jam_keluar',
            'menit_telat',
            'cepat_keluar',
            'lembur',
        ]


class AbsensiConflictGroupSerializer(serializers.Serializer):
    karyawan_id = serializers.CharField()
    karyawan_nama = serializers.CharField()
    tanggal = serializers.DateField()
    entries = AbsensiSerializer(many=True)
