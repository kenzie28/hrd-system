STATE_MANAGER_PASSWORD = 'bears'
STATE_FORMAT_MARKER = '#hrd-system-state'
STATE_FORMAT_VERSION = 'v1'
PASSWORD_HEADER = 'HTTP_X_STATE_MANAGER_PASSWORD'

TABLE_LOKASI = 'lokasi'
TABLE_AUTH_USER = 'auth_user'
TABLE_KARYAWAN = 'karyawan'
TABLE_LANGGANAN = 'langganan'
TABLE_SHIFT = 'shift'
TABLE_LIBURAN = 'liburan'
TABLE_ABSENSI = 'absensi'
TABLE_PERMOHONAN_CUTI = 'permohonan_cuti'
TABLE_NOTIFIKASI_DISMISS = 'notifikasi_dismiss'
TABLE_CUTI = 'cuti'
TABLE_PERMOHONAN_LEMBUR = 'permohonan_lembur'
TABLE_GAJI = 'gaji'

TABLE_COLUMNS = {
    TABLE_LOKASI: ('id', 'nama'),
    TABLE_AUTH_USER: (
        'id',
        'username',
        'password',
        'email',
        'is_active',
        'is_staff',
        'is_superuser',
        'date_joined',
        'last_login',
    ),
    TABLE_KARYAWAN: (
        'karyawan_id',
        'nama',
        'lokasi_kerja_id',
        'jabatan',
        'wilayah',
        'level',
        'user_id',
        'must_change_password',
        'cuti_tahunan',
    ),
    TABLE_LANGGANAN: (
        'id',
        'subscriber_id',
        'target_id',
        'created_at',
    ),
    TABLE_SHIFT: ('id', 'lokasi_kerja_id', 'hari', 'jam_masuk', 'jam_keluar'),
    TABLE_LIBURAN: ('id', 'nama', 'tanggal'),
    TABLE_ABSENSI: (
        'id',
        'karyawan_id',
        'lokasi_id',
        'tanggal',
        'jam_masuk',
        'durasi',
    ),
    TABLE_PERMOHONAN_CUTI: (
        'id',
        'karyawan_id',
        'tipe',
        'alasan',
        'tanggal_mulai',
        'tanggal_selesai',
        'status',
        'supervisor_id',
        'hrd_approver_id',
    ),
    TABLE_NOTIFIKASI_DISMISS: (
        'id',
        'subscriber_id',
        'permohonan_id',
        'dismissed_at',
    ),
    TABLE_CUTI: ('id', 'permohonan_id', 'tanggal'),
    TABLE_PERMOHONAN_LEMBUR: (
        'id',
        'karyawan_id',
        'alasan',
        'tanggal',
        'status',
        'supervisor_id',
        'hrd_approver_id',
    ),
    TABLE_GAJI: (
        'id',
        'karyawan_id',
        'periode',
        'hadir',
        'total_hadir',
        'hari_sakit',
        'hari_cuti',
        'hari_cuti_tambahan',
        'freq_pencapaian_target',
        'rate_target',
        'rate_non_target',
        'gaji_pokok',
        'rate_uang_makan',
        'freq_lembur_6_jam',
        'rate_lembur_6_jam',
        'freq_hari_raya',
        'tunjangan_lama_kerja',
        'tunjangan_obat',
        'freq_alpa',
        'pot_bpjs_jht',
        'pot_bpjs_jp',
        'pot_bpjs_kesehatan',
        'pot_pph21',
        'pot_kehilangan',
        'koreksi_absensi',
        'total_gaji',
        'created_at',
        'updated_at',
    ),
}

TABLE_ORDER = tuple(TABLE_COLUMNS.keys())
