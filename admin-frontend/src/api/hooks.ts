import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { api } from './client'
import type {
  Absensi,
  AbsensiConflictGroup,
  AbsensiImportResult,
  Cuti,
  GajiImportResult,
  GajiTemp,
  Karyawan,
  KaryawanImportResult,
  KaryawanWrite,
  Liburan,
  LiburanImportResult,
  Lokasi,
  PermohonanCuti,
  PermohonanLembur,
  RecordFilters,
  Shift,
  ShiftImportResult,
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

export function useKaryawanCreate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: KaryawanWrite) =>
      api.post<Karyawan>('/admin/karyawan/', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['karyawan'] })
    },
  })
}

export function useKaryawanUpdate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: Partial<KaryawanWrite> & { id: number }) =>
      api.patch<Karyawan>(`/admin/karyawan/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['karyawan'] })
    },
  })
}

export function useKaryawanDelete() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/admin/karyawan/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['karyawan'] })
    },
  })
}

function normalizeKaryawanImportResult(
  data: Partial<KaryawanImportResult> & { ok?: boolean },
): KaryawanImportResult {
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
    errors,
    received_headers: Array.isArray(data.received_headers) ? data.received_headers : [],
    required_columns: Array.isArray(data.required_columns) ? data.required_columns : [],
  }
}

function isKaryawanImportResult(data: unknown): data is KaryawanImportResult {
  return typeof data === 'object' && data !== null && 'errors' in data
}

function karyawanImportFailure(message: string): KaryawanImportResult {
  return normalizeKaryawanImportResult({
    ok: false,
    errors: [{ row: 0, message }],
  })
}

function parseKaryawanImportError(err: unknown): KaryawanImportResult {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (isKaryawanImportResult(data)) {
      return normalizeKaryawanImportResult(data)
    }
    if (typeof data === 'string' && data.trim()) {
      return karyawanImportFailure(data)
    }
    if (typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>
      if (typeof record.detail === 'string' && record.detail) {
        return karyawanImportFailure(record.detail)
      }
      if (Array.isArray(record.detail)) {
        return karyawanImportFailure(record.detail.map(String).join(' '))
      }
      if (typeof record.message === 'string' && record.message) {
        return karyawanImportFailure(record.message)
      }
    }
    if (err.response?.status) {
      return karyawanImportFailure(
        `Server mengembalikan status ${err.response.status}. Periksa koneksi atau hubungi admin.`,
      )
    }
    if (err.message) {
      return karyawanImportFailure(err.message)
    }
  }
  return karyawanImportFailure('Gagal mengunggah file CSV. Periksa koneksi atau coba lagi.')
}

export function useKaryawanImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      try {
        const response = await api.post<KaryawanImportResult>(
          '/admin/karyawan/import/',
          formData,
        )
        return normalizeKaryawanImportResult(response.data)
      } catch (err) {
        return parseKaryawanImportError(err)
      }
    },
    onSuccess: (result) => {
      if (result.ok) {
        qc.invalidateQueries({ queryKey: ['karyawan'] })
      }
    },
  })
}

export function useLokasi() {
  return useQuery({
    queryKey: ['lokasi'],
    queryFn: async () => (await api.get<Lokasi[]>('/lokasi/')).data,
  })
}

export function useLiburan(filters?: { bulan?: string }) {
  return useQuery({
    queryKey: ['admin-liburan', filters],
    queryFn: async () =>
      (
        await api.get<Liburan[]>('/admin/liburan/', {
          params: { bulan: filters?.bulan },
        })
      ).data,
  })
}

export function useLiburanMutations() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin-liburan'] })

  const create = useMutation({
    mutationFn: (data: Omit<Liburan, 'id'>) => api.post('/admin/liburan/', data),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, ...data }: Liburan) => api.patch(`/admin/liburan/${id}/`, data),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/liburan/${id}/`),
    onSuccess: invalidate,
  })
  return { create, update, remove }
}

function normalizeLiburanImportResult(
  data: Partial<LiburanImportResult> & { ok?: boolean },
): LiburanImportResult {
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
    errors,
    received_headers: Array.isArray(data.received_headers) ? data.received_headers : [],
    required_columns: Array.isArray(data.required_columns) ? data.required_columns : [],
  }
}

function isLiburanImportResult(data: unknown): data is LiburanImportResult {
  return typeof data === 'object' && data !== null && 'errors' in data
}

function liburanImportFailure(message: string): LiburanImportResult {
  return normalizeLiburanImportResult({
    ok: false,
    errors: [{ row: 0, message }],
  })
}

function parseLiburanImportError(err: unknown): LiburanImportResult {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (isLiburanImportResult(data)) {
      return normalizeLiburanImportResult(data)
    }
    if (typeof data === 'string' && data.trim()) {
      return liburanImportFailure(data)
    }
    if (typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>
      if (typeof record.detail === 'string' && record.detail) {
        return liburanImportFailure(record.detail)
      }
      if (Array.isArray(record.detail)) {
        return liburanImportFailure(record.detail.map(String).join(' '))
      }
      if (typeof record.message === 'string' && record.message) {
        return liburanImportFailure(record.message)
      }
    }
    if (err.response?.status) {
      return liburanImportFailure(
        `Server mengembalikan status ${err.response.status}. Periksa koneksi atau hubungi admin.`,
      )
    }
    if (err.message) {
      return liburanImportFailure(err.message)
    }
  }
  return liburanImportFailure('Gagal mengunggah file CSV. Periksa koneksi atau coba lagi.')
}

export function useLiburanImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      try {
        const response = await api.post<LiburanImportResult>(
          '/admin/liburan/import/',
          formData,
        )
        return normalizeLiburanImportResult(response.data)
      } catch (err) {
        return parseLiburanImportError(err)
      }
    },
    onSuccess: (result) => {
      if (result.ok) {
        qc.invalidateQueries({ queryKey: ['admin-liburan'] })
      }
    },
  })
}

// ---- Shift (per lokasi kerja) ----

export function useShifts(lokasiKerja?: string) {
  return useQuery({
    queryKey: ['shifts', lokasiKerja],
    queryFn: async () =>
      (
        await api.get<Shift[]>('/shifts/', {
          params: { lokasi_kerja: lokasiKerja },
        })
      ).data,
    enabled: lokasiKerja != null,
  })
}

export function useShiftMutations() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['shifts'] })

  const create = useMutation({
    mutationFn: (data: Omit<Shift, 'id' | 'lokasi_kerja_nama' | 'hari_display'>) =>
      api.post('/shifts/', data),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, ...data }: Omit<Shift, 'lokasi_kerja_nama' | 'hari_display'>) =>
      api.patch(`/shifts/${id}/`, data),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/shifts/${id}/`),
    onSuccess: invalidate,
  })
  return { create, update, remove }
}

function normalizeShiftImportResult(
  data: Partial<ShiftImportResult> & { ok?: boolean },
): ShiftImportResult {
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
    errors,
    received_headers: Array.isArray(data.received_headers) ? data.received_headers : [],
    required_columns: Array.isArray(data.required_columns) ? data.required_columns : [],
  }
}

function isShiftImportResult(data: unknown): data is ShiftImportResult {
  return typeof data === 'object' && data !== null && 'errors' in data
}

function shiftImportFailure(message: string): ShiftImportResult {
  return normalizeShiftImportResult({
    ok: false,
    errors: [{ row: 0, message }],
  })
}

function parseShiftImportError(err: unknown): ShiftImportResult {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (isShiftImportResult(data)) {
      return normalizeShiftImportResult(data)
    }
    if (typeof data === 'string' && data.trim()) {
      return shiftImportFailure(data)
    }
    if (typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>
      if (typeof record.detail === 'string' && record.detail) {
        return shiftImportFailure(record.detail)
      }
      if (Array.isArray(record.detail)) {
        return shiftImportFailure(record.detail.map(String).join(' '))
      }
      if (typeof record.message === 'string' && record.message) {
        return shiftImportFailure(record.message)
      }
    }
    if (err.response?.status) {
      return shiftImportFailure(
        `Server mengembalikan status ${err.response.status}. Periksa koneksi atau hubungi admin.`,
      )
    }
    if (err.message) {
      return shiftImportFailure(err.message)
    }
  }
  return shiftImportFailure('Gagal mengunggah file CSV. Periksa koneksi atau coba lagi.')
}

export function useShiftImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      try {
        const response = await api.post<ShiftImportResult>(
          '/admin/shift/import/',
          formData,
        )
        return normalizeShiftImportResult(response.data)
      } catch (err) {
        return parseShiftImportError(err)
      }
    },
    onSuccess: (result) => {
      if (result.ok) {
        qc.invalidateQueries({ queryKey: ['shifts'] })
      }
    },
  })
}

// ---- Absensi ----

export function useAbsensi(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['absensi', filters],
    queryFn: async () =>
      (await api.get<Absensi[]>('/absensi/', { params: filterParams(filters) })).data,
    enabled: filters?.karyawan != null,
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
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['absensi'] })
    qc.invalidateQueries({ queryKey: ['absensi-conflicts'] })
  }

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

function normalizeAbsensiImportResult(
  data: Partial<AbsensiImportResult> & { ok?: boolean },
): AbsensiImportResult {
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
    errors,
    received_headers: Array.isArray(data.received_headers) ? data.received_headers : [],
    required_columns: Array.isArray(data.required_columns) ? data.required_columns : [],
  }
}

function isAbsensiImportResult(data: unknown): data is AbsensiImportResult {
  return typeof data === 'object' && data !== null && 'errors' in data
}

function absensiImportFailure(message: string): AbsensiImportResult {
  return normalizeAbsensiImportResult({
    ok: false,
    errors: [{ row: 0, message }],
  })
}

function parseAbsensiImportError(err: unknown): AbsensiImportResult {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (isAbsensiImportResult(data)) {
      return normalizeAbsensiImportResult(data)
    }
    if (typeof data === 'string' && data.trim()) {
      return absensiImportFailure(data)
    }
    if (typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>
      if (typeof record.detail === 'string' && record.detail) {
        return absensiImportFailure(record.detail)
      }
      if (Array.isArray(record.detail)) {
        return absensiImportFailure(record.detail.map(String).join(' '))
      }
      if (typeof record.message === 'string' && record.message) {
        return absensiImportFailure(record.message)
      }
    }
    if (err.response?.status) {
      return absensiImportFailure(
        `Server mengembalikan status ${err.response.status}. Periksa koneksi atau hubungi admin.`,
      )
    }
    if (err.message) {
      return absensiImportFailure(err.message)
    }
  }
  return absensiImportFailure('Gagal mengunggah file CSV. Periksa koneksi atau coba lagi.')
}

export function useAbsensiImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      try {
        const response = await api.post<AbsensiImportResult>(
          '/admin/absensi/import/',
          formData,
        )
        return normalizeAbsensiImportResult(response.data)
      } catch (err) {
        return parseAbsensiImportError(err)
      }
    },
    onSuccess: (result) => {
      if (result.ok) {
        qc.invalidateQueries({ queryKey: ['absensi'] })
        qc.invalidateQueries({ queryKey: ['absensi-conflicts'] })
      }
    },
  })
}

// ---- Absensi conflicts (duplicate clock-in/out on the same day) ----

export function useAbsensiConflicts() {
  return useQuery({
    queryKey: ['absensi-conflicts'],
    queryFn: async () =>
      (await api.get<AbsensiConflictGroup[]>('/absensi/conflicts/')).data,
  })
}

export function useAbsensiConflictMutations() {
  const qc = useQueryClient()
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['absensi-conflicts'] })
    qc.invalidateQueries({ queryKey: ['absensi'] })
  }

  const resolve = useMutation({
    mutationFn: (id: number) =>
      api.post<Absensi>(`/absensi/${id}/resolve_conflict/`),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/absensi/${id}/`),
    onSuccess: invalidate,
  })
  return { resolve, remove }
}

// ---- Cuti (read-only) ----

export function useCuti(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['cuti', filters],
    queryFn: async () =>
      (await api.get<Cuti[]>('/cuti/', { params: filterParams(filters) })).data,
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

// ---- HRD Lembur Approval ----

export function useLembur(filters?: RecordFilters) {
  return useQuery({
    queryKey: ['admin-lembur-list', filters],
    queryFn: async () =>
      (
        await api.get<PermohonanLembur[]>('/admin/lembur/', {
          params: { status: 'APPROVED', ...filterParams(filters) },
        })
      ).data,
  })
}

export function usePendingLembur() {
  return useQuery({
    queryKey: ['admin-lembur'],
    queryFn: async () =>
      (await api.get<PermohonanLembur[]>('/admin/lembur/')).data,
  })
}

export function useLemburApprovalMutations() {
  const qc = useQueryClient()
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['admin-lembur'] })
    qc.invalidateQueries({ queryKey: ['admin-lembur-list'] })
  }

  const approve = useMutation({
    mutationFn: (id: number) => api.post(`/admin/lembur/${id}/approve/`),
    onSuccess: invalidate,
  })
  const reject = useMutation({
    mutationFn: (id: number) => api.post(`/admin/lembur/${id}/reject/`),
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
