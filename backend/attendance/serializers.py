from rest_framework import serializers

from .models import Absensi, Cuti, Jadwal, Liburan, RekapKehadiran, Shift


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ['id', 'jam_masuk', 'jam_keluar']


class JadwalSerializer(serializers.ModelSerializer):
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    shift_detail = ShiftSerializer(source='shift', read_only=True)

    class Meta:
        model = Jadwal
        fields = ['id', 'karyawan', 'karyawan_nama', 'shift', 'shift_detail', 'tanggal']


class JadwalBulkSerializer(serializers.Serializer):
    karyawan_ids = serializers.PrimaryKeyRelatedField(
        queryset=Jadwal._meta.get_field('karyawan').related_model.objects.all(),
        many=True,
    )
    shift_id = serializers.PrimaryKeyRelatedField(queryset=Shift.objects.all())
    tanggal_mulai = serializers.DateField()
    tanggal_selesai = serializers.DateField()

    def validate(self, attrs):
        if attrs['tanggal_selesai'] < attrs['tanggal_mulai']:
            raise serializers.ValidationError(
                'tanggal_selesai must not be before tanggal_mulai'
            )
        return attrs


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


class CutiSerializer(serializers.ModelSerializer):
    karyawan = serializers.IntegerField(source='permohonan.karyawan_id', read_only=True)
    karyawan_nama = serializers.CharField(
        source='permohonan.karyawan.nama', read_only=True
    )
    tipe = serializers.CharField(source='permohonan.tipe', read_only=True)
    tipe_display = serializers.CharField(
        source='permohonan.get_tipe_display', read_only=True
    )
    supervisor_nama = serializers.CharField(
        source='permohonan.supervisor.nama', read_only=True, default=None
    )

    class Meta:
        model = Cuti
        fields = [
            'id', 'permohonan', 'tanggal', 'karyawan', 'karyawan_nama',
            'tipe', 'tipe_display', 'supervisor_nama',
        ]


class RekapKehadiranSerializer(serializers.ModelSerializer):
    jadwal_detail = JadwalSerializer(source='jadwal', read_only=True)
    absensi_detail = AbsensiSerializer(source='absensi', read_only=True)
    cuti_detail = CutiSerializer(source='cuti', read_only=True)
    karyawan = serializers.IntegerField(source='jadwal.karyawan_id', read_only=True)
    karyawan_nama = serializers.CharField(source='jadwal.karyawan.nama', read_only=True)
    tanggal = serializers.DateField(source='jadwal.tanggal', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RekapKehadiran
        fields = [
            'id', 'jadwal', 'jadwal_detail', 'karyawan', 'karyawan_nama', 'tanggal',
            'absensi', 'absensi_detail', 'cuti', 'cuti_detail',
            'status', 'status_display',
        ]


class LiburanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Liburan
        fields = ['id', 'nama', 'tanggal']


class RekapProcessSerializer(serializers.Serializer):
    tanggal_mulai = serializers.DateField()
    tanggal_selesai = serializers.DateField()

    def validate(self, attrs):
        if attrs['tanggal_selesai'] < attrs['tanggal_mulai']:
            raise serializers.ValidationError(
                'tanggal_selesai must not be before tanggal_mulai'
            )
        return attrs
