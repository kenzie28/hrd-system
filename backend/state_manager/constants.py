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
TABLE_DINAS = 'dinas'
TABLE_KOREKSI = 'koreksi'
TABLE_TUNJANGAN_OBAT = 'tunjangan_obat'

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
        'base_gaji',
        'gaji_bulanan',
        'target_gaji',
        'bca_transfer',
        'status_k_tk',
        'akumulasi_lembur',
        'absensi_dihitung',
        'lembur_dibayar',
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
    TABLE_DINAS: (
        'id',
        'karyawan_id',
        'tanggal',
    ),
    TABLE_KOREKSI: (
        'id',
        'karyawan_id',
        'tipe',
        'nominal',
        'tanggal',
    ),
    TABLE_TUNJANGAN_OBAT: (
        'id',
        'karyawan_id',
        'nominal',
        'bulan',
    ),
}

TABLE_ORDER = tuple(TABLE_COLUMNS.keys())

# Older snapshots may omit these columns. Missing values default during parse.
OPTIONAL_TABLE_COLUMNS = {
    TABLE_KARYAWAN: frozenset({
        'base_gaji',
        'gaji_bulanan',
        'target_gaji',
        'bca_transfer',
        'status_k_tk',
        'akumulasi_lembur',
        'absensi_dihitung',
        'lembur_dibayar',
    }),
}

# Older snapshots may include these columns.
# permohonan_lembur.tipe is not discarded: an approved DINAS value is imported
# as a dinas row. Every other extra column here is ignored.
LEGACY_EXTRA_COLUMNS = {
    TABLE_KARYAWAN: frozenset({'jumlah_anak', 'nikah'}),
    TABLE_PERMOHONAN_LEMBUR: frozenset({'tipe'}),
}

# Older snapshots may include these tables. Their sections are ignored on import.
LEGACY_SKIPPED_TABLES = frozenset({'gaji'})

# Older snapshots may omit these tables. A missing table imports as no rows.
OPTIONAL_TABLES = frozenset({TABLE_KOREKSI, TABLE_TUNJANGAN_OBAT, TABLE_DINAS})

TABLE_KEHADIRAN = 'kehadiran'
TABLE_REKAP_ABSENSI = 'rekap_absensi'

# id, Indonesian label. Order is the checklist order in State Manager.
CLEARABLE_MODELS: tuple[tuple[str, str], ...] = (
    (TABLE_LOKASI, 'Lokasi kerja'),
    (TABLE_AUTH_USER, 'Akun login'),
    (TABLE_KARYAWAN, 'Karyawan'),
    (TABLE_LANGGANAN, 'Langganan kalender'),
    (TABLE_SHIFT, 'Shift'),
    (TABLE_LIBURAN, 'Hari libur'),
    (TABLE_ABSENSI, 'Absensi'),
    (TABLE_PERMOHONAN_CUTI, 'Permohonan cuti'),
    (TABLE_NOTIFIKASI_DISMISS, 'Notifikasi ditutup'),
    (TABLE_CUTI, 'Hari cuti'),
    (TABLE_PERMOHONAN_LEMBUR, 'Permohonan lembur'),
    (TABLE_DINAS, 'Dinas'),
    (TABLE_KOREKSI, 'Koreksi'),
    (TABLE_TUNJANGAN_OBAT, 'Tunjangan obat'),
    (TABLE_KEHADIRAN, 'Kehadiran'),
    (TABLE_REKAP_ABSENSI, 'Rekap absensi'),
)

CLEARABLE_LABELS = dict(CLEARABLE_MODELS)

# Children before parents so PROTECT / CASCADE parents can be removed afterwards.
CLEAR_ORDER = (
    TABLE_REKAP_ABSENSI,
    TABLE_KEHADIRAN,
    TABLE_KOREKSI,
    TABLE_TUNJANGAN_OBAT,
    TABLE_DINAS,
    TABLE_PERMOHONAN_LEMBUR,
    TABLE_NOTIFIKASI_DISMISS,
    TABLE_LANGGANAN,
    TABLE_CUTI,
    TABLE_PERMOHONAN_CUTI,
    TABLE_ABSENSI,
    TABLE_SHIFT,
    TABLE_LIBURAN,
    TABLE_KARYAWAN,
    TABLE_AUTH_USER,
    TABLE_LOKASI,
)
