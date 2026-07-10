import type { CutiTipe, RekapStatus } from './api/types'

export const REKAP_STATUS_COLORS: Record<RekapStatus, string> = {
  HADIR: 'green',
  TERLAMBAT: 'orange',
  PULANG_CEPAT: 'gold',
  IZIN: 'blue',
  SAKIT: 'purple',
  CUTI: 'cyan',
  ALPA: 'red',
  LIBUR: 'geekblue',
}

export const CUTI_TIPE_COLORS: Record<CutiTipe, string> = {
  IZIN: 'blue',
  IZIN_PULANG_CEPAT: 'geekblue',
  TAHUNAN: 'cyan',
  SAKIT: 'purple',
  DUKA_CITA: 'default',
  MELAHIRKAN: 'magenta',
  ISTRI_MELAHIRKAN: 'magenta',
  MENIKAH: 'gold',
  ANAK_MENIKAH: 'gold',
  KHITANAN_ANAK: 'orange',
  PEMBAPTISAN_ANAK: 'orange',
}

export const fmtTime = (t?: string | null) => (t ? t.slice(0, 5) : '-')
