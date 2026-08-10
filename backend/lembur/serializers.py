from rest_framework import serializers

from karyawan.models import Karyawan

from .models import PermohonanLembur, StatusPermohonanLembur
from .policy import eligible_supervisor_levels


class SupervisorOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Karyawan
        fields = ['id', 'karyawan_id', 'nama', 'level']


class PermohonanLemburSerializer(serializers.ModelSerializer):
    """Read serializer for a single overtime request across portal/admin."""

    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    karyawan_kode = serializers.CharField(source='karyawan.karyawan_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supervisor_nama = serializers.CharField(
        source='supervisor.nama', read_only=True, default=None
    )
    hrd_approver_nama = serializers.CharField(
        source='hrd_approver.nama', read_only=True, default=None
    )

    class Meta:
        model = PermohonanLembur
        fields = [
            'id', 'karyawan', 'karyawan_nama', 'karyawan_kode',
            'alasan', 'tanggal',
            'status', 'status_display',
            'supervisor', 'supervisor_nama',
            'hrd_approver', 'hrd_approver_nama',
        ]


class PermohonanLemburCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermohonanLembur
        fields = ['id', 'alasan', 'tanggal', 'supervisor']

    def validate(self, attrs):
        requester = self.context['karyawan']

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
        return PermohonanLembur.objects.create(
            karyawan=requester,
            status=StatusPermohonanLembur.MENUNGGU_SUPERVISOR,
            **validated_data,
        )
