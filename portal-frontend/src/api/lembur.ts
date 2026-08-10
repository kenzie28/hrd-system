import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  CreatePermohonanLemburPayload,
  PermohonanLembur,
  SupervisorOption,
} from './types'

const INVALIDATE_KEYS = [['my-lembur'], ['lembur-approvals']]

function useInvalidateLembur() {
  const qc = useQueryClient()
  return () => INVALIDATE_KEYS.forEach((key) => qc.invalidateQueries({ queryKey: key }))
}

export function useMyLembur() {
  return useQuery({
    queryKey: ['my-lembur'],
    queryFn: async () => (await api.get<PermohonanLembur[]>('/portal/lembur/')).data,
  })
}

export function useLemburSupervisorOptions() {
  return useQuery({
    queryKey: ['lembur-supervisors'],
    queryFn: async () =>
      (await api.get<SupervisorOption[]>('/portal/lembur/supervisors/')).data,
  })
}

export function useLemburApprovals(enabled: boolean) {
  return useQuery({
    queryKey: ['lembur-approvals'],
    enabled,
    queryFn: async () =>
      (await api.get<PermohonanLembur[]>('/portal/lembur/approvals/')).data,
  })
}

export function useCreateLembur() {
  const invalidate = useInvalidateLembur()
  return useMutation({
    mutationFn: (data: CreatePermohonanLemburPayload) =>
      api.post<PermohonanLembur>('/portal/lembur/', data),
    onSuccess: invalidate,
  })
}

export function useCancelLembur() {
  const invalidate = useInvalidateLembur()
  return useMutation({
    mutationFn: (id: number) => api.post(`/portal/lembur/${id}/cancel/`),
    onSuccess: invalidate,
  })
}

export function useApproveLembur() {
  const invalidate = useInvalidateLembur()
  return useMutation({
    mutationFn: (id: number) => api.post(`/portal/lembur/${id}/approve/`),
    onSuccess: invalidate,
  })
}

export function useRejectLembur() {
  const invalidate = useInvalidateLembur()
  return useMutation({
    mutationFn: (id: number) => api.post(`/portal/lembur/${id}/reject/`),
    onSuccess: invalidate,
  })
}
