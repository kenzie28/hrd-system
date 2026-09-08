from rest_framework import serializers

from cuti.models import Cuti, PermohonanCuti
from karyawan.models import Karyawan

from .models import Langganan


class LanggananSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.CharField(source='target.karyawan_id', read_only=True)
    nama = serializers.CharField(source='target.nama', read_only=True)
    jabatan = serializers.CharField(source='target.jabatan', read_only=True)

    class Meta:
        model = Langganan
        fields = ['id', 'karyawan_id', 'nama', 'jabatan', 'created_at']


class LanggananCreateSerializer(serializers.Serializer):
    karyawan_id = serializers.CharField()


class KaryawanSearchSerializer(serializers.ModelSerializer):
    sudah_di_grup = serializers.SerializerMethodField()

    class Meta:
        model = Karyawan
        fields = ['karyawan_id', 'nama', 'jabatan', 'sudah_di_grup']

    def get_sudah_di_grup(self, obj):
        subscribed = self.context.get('subscribed_ids') or set()
        return obj.karyawan_id in subscribed


class NotifikasiSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.PrimaryKeyRelatedField(source='karyawan', read_only=True)
    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    tipe_display = serializers.CharField(source='get_tipe_display', read_only=True)

    class Meta:
        model = PermohonanCuti
        fields = [
            'id',
            'karyawan_id',
            'karyawan_nama',
            'tipe',
            'tipe_display',
            'tanggal_mulai',
            'tanggal_selesai',
        ]


class KalenderHariSerializer(serializers.ModelSerializer):
    karyawan_id = serializers.CharField(
        source='permohonan.karyawan_id', read_only=True
    )
    karyawan_nama = serializers.CharField(
        source='permohonan.karyawan.nama', read_only=True
    )
    tipe = serializers.CharField(source='permohonan.tipe', read_only=True)
    tipe_display = serializers.CharField(
        source='permohonan.get_tipe_display', read_only=True
    )
    permohonan_id = serializers.IntegerField(source='permohonan.pk', read_only=True)
    tanggal_mulai = serializers.DateField(
        source='permohonan.tanggal_mulai', read_only=True
    )
    tanggal_selesai = serializers.DateField(
        source='permohonan.tanggal_selesai', read_only=True
    )

    class Meta:
        model = Cuti
        fields = [
            'id',
            'tanggal',
            'karyawan_id',
            'karyawan_nama',
            'tipe',
            'tipe_display',
            'permohonan_id',
            'tanggal_mulai',
            'tanggal_selesai',
        ]
