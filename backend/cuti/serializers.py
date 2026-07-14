from rest_framework import serializers

from karyawan.models import Karyawan

from .models import Cuti, PermohonanCuti, StatusPermohonanCuti, TipeCuti
from .policy import eligible_supervisor_levels


class CutiSerializer(serializers.ModelSerializer):
    """Read-only per-day leave ledger row (used by the admin Rekap/Cuti views)."""

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


class SupervisorOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = ['id', 'karyawan_id', 'nama', 'level']


class PermohonanCutiSerializer(serializers.ModelSerializer):
    """Read serializer for a single leave request across all portals/admin."""

    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    karyawan_kode = serializers.CharField(source='karyawan.karyawan_id', read_only=True)
    tipe_display = serializers.CharField(source='get_tipe_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supervisor_nama = serializers.CharField(
        source='supervisor.nama', read_only=True, default=None
    )
    hrd_approver_nama = serializers.CharField(
        source='hrd_approver.nama', read_only=True, default=None
    )
    jumlah_hari = serializers.SerializerMethodField()

    class Meta:
        model = PermohonanCuti
        fields = [
            'id', 'karyawan', 'karyawan_nama', 'karyawan_kode',
            'tipe', 'tipe_display', 'alasan',
            'tanggal_mulai', 'tanggal_selesai', 'jumlah_hari',
            'status', 'status_display',
            'supervisor', 'supervisor_nama',
            'hrd_approver', 'hrd_approver_nama',
        ]

    def get_jumlah_hari(self, obj):
        return (obj.tanggal_selesai - obj.tanggal_mulai).days + 1


class PermohonanCutiCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermohonanCuti
        fields = ['id', 'tipe', 'alasan', 'tanggal_mulai', 'tanggal_selesai', 'supervisor']

    def validate_tipe(self, value):
        if value not in TipeCuti.values:
            raise serializers.ValidationError('Tipe cuti tidak valid.')
        return value

    def validate(self, attrs):
        requester = self.context['karyawan']
        if attrs['tanggal_selesai'] < attrs['tanggal_mulai']:
            raise serializers.ValidationError(
                {'tanggal_selesai': 'Tanggal selesai tidak boleh sebelum tanggal mulai.'}
            )

        supervisor = attrs.get('supervisor')
        if supervisor is None:
            raise serializers.ValidationError({'supervisor': 'Supervisor wajib dipilih.'})
        if supervisor.id == requester.id:
            raise serializers.ValidationError(
                {'supervisor': 'Anda tidak dapat memilih diri sendiri sebagai supervisor.'}
            )

        allowed = eligible_supervisor_levels(requester.level)
        if supervisor.level not in allowed:
            raise serializers.ValidationError(
                {'supervisor': f'Supervisor harus berada di level {allowed or "-"}.'}
            )
        return attrs

    def create(self, validated_data):
        requester = self.context['karyawan']
        return PermohonanCuti.objects.create(
            karyawan=requester,
            status=StatusPermohonanCuti.MENUNGGU_SUPERVISOR,
            **validated_data,
        )
