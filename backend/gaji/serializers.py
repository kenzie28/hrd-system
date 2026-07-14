from rest_framework import serializers

from .models import GajiTemp


class GajiTempSerializer(serializers.ModelSerializer):
    """Full payroll breakdown for one karyawan/periode, including the
    computed properties. Used by both the portal detail endpoint and the
    admin review list."""

    karyawan_nama = serializers.CharField(source='karyawan.nama', read_only=True)
    karyawan_kode = serializers.CharField(source='karyawan.karyawan_id', read_only=True)

    nominal_target = serializers.IntegerField(read_only=True)
    freq_hari_non_target = serializers.IntegerField(read_only=True)
    nominal_non_target = serializers.IntegerField(read_only=True)
    nominal_uang_makan = serializers.IntegerField(read_only=True)
    rate_hari_raya = serializers.IntegerField(read_only=True)
    nominal_lembur = serializers.IntegerField(read_only=True)
    nominal_hari_raya = serializers.IntegerField(read_only=True)
    pengurang_alpa = serializers.IntegerField(read_only=True)

    class Meta:
        model = GajiTemp
        fields = [
            'id',
            'karyawan',
            'karyawan_nama',
            'karyawan_kode',
            'periode',
            'hadir',
            'total_hadir',
            'hari_sakit',
            'hari_cuti',
            'hari_cuti_tambahan',
            'freq_pencapaian_target',
            'rate_target',
            'nominal_target',
            'freq_hari_non_target',
            'rate_non_target',
            'nominal_non_target',
            'gaji_pokok',
            'rate_uang_makan',
            'nominal_uang_makan',
            'freq_lembur_6_jam',
            'rate_lembur_6_jam',
            'nominal_lembur',
            'freq_hari_raya',
            'rate_hari_raya',
            'nominal_hari_raya',
            'tunjangan_lama_kerja',
            'tunjangan_obat',
            'freq_alpa',
            'pengurang_alpa',
            'pot_bpjs_jht',
            'pot_bpjs_jp',
            'pot_bpjs_kesehatan',
            'pot_pph21',
            'pot_kehilangan',
            'koreksi_absensi',
            'total_gaji',
        ]
