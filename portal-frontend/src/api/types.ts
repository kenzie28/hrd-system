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

export interface GajiComponent {
  label: string
  amount: number
}

export interface GajiResponse {
  karyawan: PortalKaryawan
  bulan: string | null
  components: GajiComponent[]
  total: number
}
