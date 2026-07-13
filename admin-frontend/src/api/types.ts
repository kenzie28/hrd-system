export interface Shift {
  id: number
  jam_masuk: string
  jam_keluar: string
}

export interface Karyawan {
  id: number
  karyawan_id: string
  nama: string
  lokasi_kerja: string | null
  jabatan: string
  wilayah: string
  level: number
  default_shift: number | null
}

export interface Lokasi {
  id: string
  nama: string
}

export interface Liburan {
  id: number
  nama: string
  tanggal: string
}

export interface Jadwal {
  id: number
  karyawan: number
  karyawan_nama: string
  shift: number
  shift_detail: Shift
  tanggal: string
}

export interface Absensi {
  id: number
  karyawan: number
  karyawan_nama: string
  lokasi: string
  lokasi_nama: string
  tanggal: string
  jam_masuk: string
  durasi: string
  jam_keluar: string
  keluar_hari_offset: number
}

export type CutiTipe =
  | 'IZIN'
  | 'IZIN_PULANG_CEPAT'
  | 'TAHUNAN'
  | 'SAKIT'
  | 'DUKA_CITA'
  | 'MELAHIRKAN'
  | 'ISTRI_MELAHIRKAN'
  | 'MENIKAH'
  | 'ANAK_MENIKAH'
  | 'KHITANAN_ANAK'
  | 'PEMBAPTISAN_ANAK'

export interface Cuti {
  id: number
  permohonan: number
  tanggal: string
  karyawan: number
  karyawan_nama: string
  tipe: CutiTipe
  tipe_display: string
  supervisor_nama: string | null
}

export type RekapStatus =
  | 'HADIR'
  | 'TERLAMBAT'
  | 'PULANG_CEPAT'
  | 'IZIN'
  | 'SAKIT'
  | 'CUTI'
  | 'ALPA'
  | 'LIBUR'

export interface Rekap {
  id: number
  jadwal: number
  jadwal_detail: Jadwal
  karyawan: number
  karyawan_nama: string
  tanggal: string
  absensi: number | null
  absensi_detail: Absensi | null
  cuti: number | null
  cuti_detail: Cuti | null
  status: RekapStatus
  status_display: string
}

export interface RecordFilters {
  karyawan?: number
  bulan?: string
}

export interface AdminKaryawan {
  id: number
  karyawan_id: string
  nama: string
  level: number
  must_change_password: boolean
}

export interface AdminLoginResponse {
  token: string
  karyawan: AdminKaryawan
}

export interface ChangePasswordResponse {
  token: string
  must_change_password: boolean
}

export type CutiStatus =
  | 'MENUNGGU_SUPERVISOR'
  | 'MENUNGGU_HRD'
  | 'DITOLAK'
  | 'DIBATALKAN'
  | 'APPROVED'

export interface PermohonanCuti {
  id: number
  karyawan: number
  karyawan_nama: string
  karyawan_kode: string
  tipe: CutiTipe
  tipe_display: string
  alasan: string
  tanggal_mulai: string
  tanggal_selesai: string
  jumlah_hari: number
  status: CutiStatus
  status_display: string
  supervisor: number | null
  supervisor_nama: string | null
  hrd_approver: number | null
  hrd_approver_nama: string | null
}

export interface GajiTemp {
  id: number
  karyawan: number
  karyawan_nama: string
  karyawan_kode: string
  periode: string
  hadir: number
  hari_sakit: number
  hari_cuti: number
  hari_cuti_tambahan: number
  freq_pencapaian_target: number
  rate_target: number
  nominal_target: number
  freq_hari_non_target: number
  rate_non_target: number
  nominal_non_target: number
  gaji_pokok: number
  rate_uang_makan: number
  nominal_uang_makan: number
  freq_lembur_6_jam: string
  rate_lembur_6_jam: number
  nominal_lembur: number
  freq_hari_raya: number
  rate_hari_raya: number
  nominal_hari_raya: number
  tunjangan_lama_kerja: number
  tunjangan_obat: number
  freq_alpa: number
  pengurang_alpa: number
  pot_bpjs_jht: number
  pot_bpjs_jp: number
  pot_bpjs_kesehatan: number
  pot_pph21: number
  pot_kehilangan: number
  koreksi_absensi: number
  total_gaji: number
}

export interface GajiImportError {
  row: number
  message: string
}

export interface GajiImportResult {
  ok: boolean
  total_rows: number
  created: number
  updated: number
  karyawan_created: number
  errors: GajiImportError[]
  received_headers: string[]
  required_columns: string[]
}
