import type { CutiStatus, CutiTipe } from './api/types'

// Mirror of backend cuti/policy.py LEVEL_APPROVER_MAP. Keep both in sync.
// Maps a requester's level to the supervisor levels they may request.
export const LEVEL_APPROVER_MAP: Record<number, number[]> = {
  1: [5, 6, 7],
  2: [5, 6, 7],
  3: [5, 6, 7],
  4: [5, 6, 7],
  5: [7],
  6: [7],
  7: [8],
}

// Employees at this level or above can approve requests (Persetujuan tab).
export const MIN_SUPERVISOR_LEVEL = 5

export const eligibleSupervisorLevels = (level: number): number[] =>
  LEVEL_APPROVER_MAP[level] ?? []

export const CUTI_TIPE_OPTIONS: { value: CutiTipe; label: string }[] = [
  { value: 'IZIN_OFF', label: 'Izin Off' },
  { value: 'IZIN_TELAT', label: 'Izin Telat' },
  { value: 'IZIN_PULANG_CEPAT', label: 'Izin Pulang Cepat' },
  { value: 'IZIN_LOKASI_BEDA', label: 'Izin Absen di Lokasi Beda' },
  { value: 'CUTI_TAHUNAN', label: 'Cuti Tahunan' },
  { value: 'CUTI_SAKIT', label: 'Cuti Sakit' },
  { value: 'CUTI_DUKA_CITA', label: 'Cuti Duka Cita' },
  { value: 'CUTI_MELAHIRKAN', label: 'Cuti Melahirkan' },
  { value: 'CUTI_ISTRI_MELAHIRKAN', label: 'Cuti Istri Melahirkan' },
  { value: 'CUTI_MENIKAH', label: 'Cuti Menikah' },
  { value: 'CUTI_ANAK_MENIKAH', label: 'Cuti Anak Menikah' },
  { value: 'CUTI_KHITANAN_ANAK', label: 'Cuti Khitanan Anak' },
  { value: 'CUTI_PEMBAPTISAN_ANAK', label: 'Cuti Pembaptisan Anak' },
]

export const CUTI_STATUS_COLORS: Record<CutiStatus, string> = {
  MENUNGGU_SUPERVISOR: 'orange',
  MENUNGGU_HRD: 'blue',
  DITOLAK: 'red',
  DIBATALKAN: 'default',
  APPROVED: 'green',
}

const currencyFormatter = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0,
})

export const formatCurrency = (value: number) => currencyFormatter.format(value)
