import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  Absensi,
  Cuti,
  Jadwal,
  Karyawan,
  Liburan,
  Lokasi,
  PermohonanCuti,
  RecordFilters,
  Rekap,
  Shift,
} from './types'

function filterParams(filters?: RecordFilters) {
  return {
    karyawan: filters?.karyawan,
    bulan: filters?.bulan,
  }
}

export function useKaryawan() {
  return useQuery({
    queryKey: ['karyawan'],
    queryFn: async () => (await api.get<Karyawan[]>('/karyawan/')).data,
  })
}

export function useLokasi() {
  return useQuery({
    queryKey: ['lokasi'],
    queryFn: async () => (await api.get<Lokasi[]>('/lokasi/')).data,
  })
}

export function useLiburan() {
  return useQuery({
    queryKey: ['liburan'],
    queryFn: async () => (await api.get<Liburan[]>('/liburan/')).data,
  })
}

// ---- Shift ----

export function useShifts() {
  return useQuery({
    queryKey: ['shifts'],
    queryFn: async () => (await api.get<Shift[]>('/shifts/')).data,
  })
}

export function useShiftMutations() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['shifts'] })

  const create = useMutation({
    mutationFn: (data: Omit<Shift, 'id'>) => api.post('/shifts/', data),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, ...data }: Shift) => api.patch(`/shifts/${id}/`, data),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/shifts/${id}/`),
    onSuccess: invalidate,
  })
  return { create, update, remove }
}

// ---- Jadwal ----

export function useJadwal(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['jadwal', filters],
    queryFn: async () =>
      (await api.get<Jadwal[]>('/jadwal/', { params: filterParams(filters) })).data,
  })
}

export interface JadwalBulkPayload {
  karyawan_ids: number[]
  shift_id: number
  tanggal_mulai: string
  tanggal_selesai: string
}

export function useJadwalMutations() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['jadwal'] })

  const bulkCreate = useMutation({
    mutationFn: (data: JadwalBulkPayload) =>
      api.post<{ created: number; skipped_existing: number }>('/jadwal/bulk/', data),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, shift }: { id: number; shift: number }) =>
      api.patch(`/jadwal/${id}/`, { shift }),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/jadwal/${id}/`),
    onSuccess: invalidate,
  })
  return { bulkCreate, update, remove }
}

// ---- Absensi ----

export function useAbsensi(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['absensi', filters],
    queryFn: async () =>
      (await api.get<Absensi[]>('/absensi/', { params: filterParams(filters) })).data,
  })
}

export interface AbsensiUpdatePayload {
  id: number
  lokasi: string
  jam_masuk: string
  durasi: string
}

export function useAbsensiMutations() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['absensi'] })

  const update = useMutation({
    mutationFn: ({ id, ...data }: AbsensiUpdatePayload) =>
      api.patch(`/absensi/${id}/`, data),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/absensi/${id}/`),
    onSuccess: invalidate,
  })
  return { update, remove }
}

// ---- Cuti (read-only) ----

export function useCuti(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['cuti', filters],
    queryFn: async () =>
      (await api.get<Cuti[]>('/cuti/', { params: filterParams(filters) })).data,
  })
}

// ---- Rekap ----

export function useRekap(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['rekap', filters],
    queryFn: async () =>
      (await api.get<Rekap[]>('/rekap/', { params: filterParams(filters) })).data,
  })
}

export function useRekapProcess() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { tanggal_mulai: string; tanggal_selesai: string }) =>
      api.post<{ processed: number }>('/rekap/process/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rekap'] }),
  })
}

// ---- HRD Cuti Approval ----

export function usePendingCuti() {
  return useQuery({
    queryKey: ['admin-cuti'],
    queryFn: async () =>
      (await api.get<PermohonanCuti[]>('/admin/cuti/')).data,
  })
}

export function useCutiApprovalMutations() {
  const qc = useQueryClient()
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['admin-cuti'] })
    qc.invalidateQueries({ queryKey: ['cuti'] })
  }

  const approve = useMutation({
    mutationFn: (id: number) => api.post(`/admin/cuti/${id}/approve/`),
    onSuccess: invalidate,
  })
  const reject = useMutation({
    mutationFn: (id: number) => api.post(`/admin/cuti/${id}/reject/`),
    onSuccess: invalidate,
  })
  return { approve, reject }
}

// ---- Reset Password ----

export function useResetPassword() {
  return useMutation({
    mutationFn: (karyawanId: number) =>
      api.post(`/admin/karyawan/${karyawanId}/reset-password/`).then((r) => r.data),
  })
}
