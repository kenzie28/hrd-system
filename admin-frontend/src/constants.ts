import type { CutiTipe, HariKerja } from './api/types'

export const HARI_KERJA_OPTIONS: { label: string; value: HariKerja }[] = [
  { label: 'Senin', value: 'SENIN' },
  { label: 'Selasa', value: 'SELASA' },
  { label: 'Rabu', value: 'RABU' },
  { label: 'Kamis', value: 'KAMIS' },
  { label: 'Jumat', value: 'JUMAT' },
  { label: 'Sabtu', value: 'SABTU' },
  { label: 'Minggu', value: 'MINGGU' },
]

export const HARI_KERJA_ORDER: Record<HariKerja, number> = {
  SENIN: 0,
  SELASA: 1,
  RABU: 2,
  KAMIS: 3,
  JUMAT: 4,
  SABTU: 5,
  MINGGU: 6,
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
