import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  CutiNotifikasi,
  KalenderHari,
  KaryawanSearchHit,
  Langganan,
} from './types'

const INVALIDATE_KEYS = [
  ['kb-langganan'],
  ['kb-notifikasi'],
  ['kb-kalender'],
  ['kb-karyawan-search'],
]

function useInvalidateKalenderBersama() {
  const qc = useQueryClient()
  return () =>
    INVALIDATE_KEYS.forEach((key) => qc.invalidateQueries({ queryKey: key }))
}

export function useLangganan() {
  return useQuery({
    queryKey: ['kb-langganan'],
    queryFn: async () =>
      (await api.get<Langganan[]>('/portal/kalender-bersama/langganan/')).data,
  })
}

export function useKaryawanSearch(q: string) {
  const query = q.trim()
  return useQuery({
    queryKey: ['kb-karyawan-search', query],
    enabled: query.length >= 2,
    queryFn: async () =>
      (
        await api.get<KaryawanSearchHit[]>('/portal/kalender-bersama/karyawan/', {
          params: { q: query },
        })
      ).data,
  })
}

export function useSubscribe() {
  const invalidate = useInvalidateKalenderBersama()
  return useMutation({
    mutationFn: (karyawanId: string) =>
      api.post<Langganan>('/portal/kalender-bersama/langganan/', {
        karyawan_id: karyawanId,
      }),
    onSuccess: invalidate,
  })
}

export function useUnsubscribe() {
  const invalidate = useInvalidateKalenderBersama()
  return useMutation({
    mutationFn: (karyawanId: string) =>
      api.delete(`/portal/kalender-bersama/langganan/${karyawanId}/`),
    onSuccess: invalidate,
  })
}

export function useNotifikasi() {
  return useQuery({
    queryKey: ['kb-notifikasi'],
    queryFn: async () =>
      (await api.get<CutiNotifikasi[]>('/portal/kalender-bersama/notifikasi/'))
        .data,
  })
}

export function useDismissNotifikasi() {
  const invalidate = useInvalidateKalenderBersama()
  return useMutation({
    mutationFn: (permohonanId: number) =>
      api.post(`/portal/kalender-bersama/notifikasi/${permohonanId}/dismiss/`),
    onSuccess: invalidate,
  })
}

export function useKalender(dari: string, sampai: string) {
  return useQuery({
    queryKey: ['kb-kalender', dari, sampai],
    queryFn: async () =>
      (
        await api.get<KalenderHari[]>('/portal/kalender-bersama/kalender/', {
          params: { dari, sampai },
        })
      ).data,
  })
}
