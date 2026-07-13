import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { api } from './client'
import type {
  Absensi,
  Cuti,
  GajiImportResult,
  GajiTemp,
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

// ---- Gaji ----

export function useGajiTemp(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['admin-gaji', filters],
    queryFn: async () =>
      (await api.get<GajiTemp[]>('/admin/gaji/', { params: filterParams(filters) })).data,
  })
}

function normalizeGajiImportResult(data: Partial<GajiImportResult> & { ok?: boolean }): GajiImportResult {
  const errors = Array.isArray(data.errors)
    ? data.errors.map((e) => ({
        row: typeof e?.row === 'number' ? e.row : 0,
        message: String(e?.message ?? 'Error tidak diketahui.'),
      }))
    : []

  return {
    ok: Boolean(data.ok),
    total_rows: data.total_rows ?? 0,
    created: data.created ?? 0,
    updated: data.updated ?? 0,
    karyawan_created: data.karyawan_created ?? 0,
    errors,
    received_headers: Array.isArray(data.received_headers) ? data.received_headers : [],
    required_columns: Array.isArray(data.required_columns) ? data.required_columns : [],
  }
}

function isGajiImportResult(data: unknown): data is GajiImportResult {
  return typeof data === 'object' && data !== null && 'errors' in data
}

function gajiImportFailure(message: string): GajiImportResult {
  return normalizeGajiImportResult({
    ok: false,
    errors: [{ row: 0, message }],
  })
}

function parseImportError(err: unknown): GajiImportResult {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (isGajiImportResult(data)) {
      return normalizeGajiImportResult(data)
    }
    if (typeof data === 'string' && data.trim()) {
      return gajiImportFailure(data)
    }
    if (typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>
      if (typeof record.detail === 'string' && record.detail) {
        return gajiImportFailure(record.detail)
      }
      if (Array.isArray(record.detail)) {
        return gajiImportFailure(record.detail.map(String).join(' '))
      }
      if (typeof record.message === 'string' && record.message) {
        return gajiImportFailure(record.message)
      }
    }
    if (err.response?.status) {
      return gajiImportFailure(
        `Server mengembalikan status ${err.response.status}. Periksa koneksi atau hubungi admin.`,
      )
    }
    if (err.message) {
      return gajiImportFailure(err.message)
    }
  }
  return gajiImportFailure('Gagal mengunggah file CSV. Periksa koneksi atau coba lagi.')
}

export function useGajiImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, upsertKaryawan }: { file: File; upsertKaryawan: boolean }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('upsert_karyawan', String(upsertKaryawan))
      try {
        const response = await api.post<GajiImportResult>('/admin/gaji/import/', formData)
        return normalizeGajiImportResult(response.data)
      } catch (err) {
        return parseImportError(err)
      }
    },
    onSuccess: (result) => {
      if (result.ok) {
        qc.invalidateQueries({ queryKey: ['admin-gaji'] })
        qc.invalidateQueries({ queryKey: ['karyawan'] })
        qc.invalidateQueries({ queryKey: ['lokasi'] })
      }
    },
  })
}

// ---- Reset Password ----

export function useResetPassword() {
  return useMutation({
    mutationFn: (karyawanId: number) =>
      api.post(`/admin/karyawan/${karyawanId}/reset-password/`).then((r) => r.data),
  })
}
