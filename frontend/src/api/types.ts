export interface Shift {
  id: number
  jam_masuk: string
  jam_keluar: string
}

export interface Karyawan {
  id: number
  nama: string
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
