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
  | 'MENUNGGU_PEMBATALAN_SUPERVISOR'
  | 'MENUNGGU_PEMBATALAN_HRD'

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
  can_batal: boolean
}

export interface CreatePermohonanCutiPayload {
  tipe: CutiTipe
  alasan?: string
  tanggal_mulai: string
  tanggal_selesai: string
  supervisor: string
}

export type TipeLembur = 'BIASA' | 'DINAS'

export interface PermohonanLembur {
  id: number
  karyawan_id: string
  karyawan_nama: string
  alasan: string
  tanggal: string
  tipe: TipeLembur
  tipe_display: string
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

export interface Kehadiran {
  id: number
  tanggal: string
  karyawan_id: string
  status: 'HADIR' | 'CUTI' | 'ALPA'
  status_display: string
  shift_jam_masuk: string | null
  shift_jam_keluar: string | null
  menit_telat: number
  cepat_keluar: number
  lembur: number
  absensi: Absensi | null
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

export interface Langganan {
  id: number
  karyawan_id: string
  nama: string
  jabatan: string
  created_at: string
}

export interface KaryawanSearchHit {
  karyawan_id: string
  nama: string
  jabatan: string
  sudah_di_grup: boolean
}

export interface CutiNotifikasi {
  id: number
  karyawan_id: string
  karyawan_nama: string
  tipe: CutiTipe
  tipe_display: string
  tanggal_mulai: string
  tanggal_selesai: string
}

export interface KalenderHari {
  id: number
  tanggal: string
  karyawan_id: string
  karyawan_nama: string
  tipe: CutiTipe
  tipe_display: string
  permohonan_id: number
  tanggal_mulai: string
  tanggal_selesai: string
}
