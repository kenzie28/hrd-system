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
  IZIN_OFF: 'blue',
  IZIN_TELAT: 'blue',
  IZIN_PULANG_CEPAT: 'geekblue',
  IZIN_LOKASI_BEDA: 'geekblue',
  CUTI_TAHUNAN: 'cyan',
  CUTI_SAKIT: 'purple',
  CUTI_DUKA_CITA: 'default',
  CUTI_MELAHIRKAN: 'magenta',
  CUTI_ISTRI_MELAHIRKAN: 'magenta',
  CUTI_MENIKAH: 'gold',
  CUTI_ANAK_MENIKAH: 'gold',
  CUTI_KHITANAN_ANAK: 'orange',
  CUTI_PEMBAPTISAN_ANAK: 'orange',
}

export const fmtTime = (t?: string | null) => (t ? t.slice(0, 5) : '-')

const currencyFormatter = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0,
})

export const formatCurrency = (value: number) => currencyFormatter.format(value)
