export interface PortalKaryawan {
  id: number
  karyawan_id: string
  nama: string
  level: number
  must_change_password: boolean
}

export type CutiTipe =
  | 'IZIN'
  | 'IZIN_TELAT'
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

export type CutiStatus =
  | 'MENUNGGU_SUPERVISOR'
  | 'MENUNGGU_HRD'
  | 'DITOLAK'
  | 'DIBATALKAN'
  | 'APPROVED'

export interface SupervisorOption {
  id: number
  karyawan_id: string
  nama: string
  level: number
}

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

export interface CreatePermohonanCutiPayload {
  tipe: CutiTipe
  alasan?: string
  tanggal_mulai: string
  tanggal_selesai: string
  supervisor: number
}

export interface LoginResponse {
  token: string
  must_change_password: boolean
  karyawan: PortalKaryawan
}

export interface ChangePasswordResponse {
  token: string
  must_change_password: boolean
}

export interface GajiDetail {
  id: number
  karyawan: number
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

export interface GajiResponse {
  karyawan: PortalKaryawan
  bulan: string | null
  gaji: GajiDetail | null
}
