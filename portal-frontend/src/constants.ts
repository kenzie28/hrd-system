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
  { value: 'IZIN', label: 'Izin' },
  { value: 'IZIN_TELAT', label: 'Izin Telat' },
  { value: 'IZIN_PULANG_CEPAT', label: 'Izin Pulang Cepat' },
  { value: 'TAHUNAN', label: 'Tahunan' },
  { value: 'SAKIT', label: 'Sakit' },
  { value: 'DUKA_CITA', label: 'Duka Cita' },
  { value: 'MELAHIRKAN', label: 'Melahirkan' },
  { value: 'ISTRI_MELAHIRKAN', label: 'Istri Melahirkan' },
  { value: 'MENIKAH', label: 'Menikah' },
  { value: 'ANAK_MENIKAH', label: 'Anak Menikah' },
  { value: 'KHITANAN_ANAK', label: 'Khitanan Anak' },
  { value: 'PEMBAPTISAN_ANAK', label: 'Pembaptisan Anak' },
]

export const CUTI_STATUS_COLORS: Record<CutiStatus, string> = {
  MENUNGGU_SUPERVISOR: 'orange',
  MENUNGGU_HRD: 'blue',
  DITOLAK: 'red',
  DIBATALKAN: 'default',
  APPROVED: 'green',
}
