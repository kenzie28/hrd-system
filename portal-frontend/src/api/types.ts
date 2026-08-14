export interface PortalKaryawan {
  karyawan_id: string
  nama: string
  level: number
  must_change_password: boolean
  cuti_tahunan: number
}

export type CutiTipe =
  | 'IZIN_OFF'
  | 'IZIN_TELAT'
  | 'IZIN_PULANG_CEPAT'
  | 'IZIN_LOKASI_BEDA'
  | 'CUTI_TAHUNAN'
  | 'CUTI_SAKIT'
  | 'CUTI_DUKA_CITA'
  | 'CUTI_MELAHIRKAN'
  | 'CUTI_ISTRI_MELAHIRKAN'
  | 'CUTI_MENIKAH'
  | 'CUTI_ANAK_MENIKAH'
  | 'CUTI_KHITANAN_ANAK'
  | 'CUTI_PEMBAPTISAN_ANAK'

export type CutiStatus =
  | 'MENUNGGU_SUPERVISOR'
  | 'MENUNGGU_HRD'
  | 'DITOLAK'
  | 'DIBATALKAN'
  | 'APPROVED'

export type LemburStatus =
  | 'MENUNGGU_SUPERVISOR'
  | 'MENUNGGU_HRD'
  | 'DITOLAK'
  | 'DIBATALKAN'
  | 'APPROVED'

export interface SupervisorOption {
  karyawan_id: string
  nama: string
  level: number
}

export interface PermohonanCuti {
  id: number
  karyawan_id: string
  karyawan_nama: string
  tipe: CutiTipe
  tipe_display: string
  alasan: string
  tanggal_mulai: string
  tanggal_selesai: string
  jumlah_hari: number
  status: CutiStatus
  status_display: string
  supervisor: string | null
  supervisor_nama: string | null
  hrd_approver: string | null
  hrd_approver_nama: string | null
}

export interface CreatePermohonanCutiPayload {
  tipe: CutiTipe
  alasan?: string
  tanggal_mulai: string
  tanggal_selesai: string
  supervisor: string
}

export interface PermohonanLembur {
  id: number
  karyawan_id: string
  karyawan_nama: string
  alasan: string
  tanggal: string
  status: LemburStatus
  status_display: string
  supervisor: string | null
  supervisor_nama: string | null
  hrd_approver: string | null
  hrd_approver_nama: string | null
}

export interface CreatePermohonanLemburPayload {
  alasan?: string
  tanggal: string
  supervisor: string
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
  karyawan_id: string
  periode: string
  hadir: string
  total_hadir: number
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

export interface Absensi {
  id: number
  karyawan_id: string
  lokasi: string
  lokasi_nama: string
  tanggal: string
  jam_masuk: string
  durasi: string
  jam_keluar: string
  keluar_hari_offset: number
}
