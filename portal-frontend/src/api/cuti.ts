import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  CreatePermohonanCutiPayload,
  PermohonanCuti,
  SupervisorOption,
} from './types'

const INVALIDATE_KEYS = [['my-cuti'], ['cuti-approvals']]

function useInvalidateCuti() {
  const qc = useQueryClient()
  return () => INVALIDATE_KEYS.forEach((key) => qc.invalidateQueries({ queryKey: key }))
}

export function useMyCuti() {
  return useQuery({
    queryKey: ['my-cuti'],
    queryFn: async () => (await api.get<PermohonanCuti[]>('/portal/cuti/')).data,
  })
}

export function useSupervisorOptions() {
  return useQuery({
    queryKey: ['cuti-supervisors'],
    queryFn: async () =>
      (await api.get<SupervisorOption[]>('/portal/cuti/supervisors/')).data,
  })
}

export function useCutiApprovals(enabled: boolean) {
  return useQuery({
    queryKey: ['cuti-approvals'],
    enabled,
    queryFn: async () =>
      (await api.get<PermohonanCuti[]>('/portal/cuti/approvals/')).data,
  })
}

export function useCreateCuti() {
  const invalidate = useInvalidateCuti()
  return useMutation({
    mutationFn: (data: CreatePermohonanCutiPayload) =>
      api.post<PermohonanCuti>('/portal/cuti/', data),
    onSuccess: invalidate,
  })
}

export function useCancelCuti() {
  const invalidate = useInvalidateCuti()
  return useMutation({
    mutationFn: (id: number) => api.post(`/portal/cuti/${id}/cancel/`),
    onSuccess: invalidate,
  })
}

export function useApproveCuti() {
  const invalidate = useInvalidateCuti()
  return useMutation({
    mutationFn: (id: number) => api.post(`/portal/cuti/${id}/approve/`),
    onSuccess: invalidate,
  })
}

export function useRejectCuti() {
  const invalidate = useInvalidateCuti()
  return useMutation({
    mutationFn: (id: number) => api.post(`/portal/cuti/${id}/reject/`),
    onSuccess: invalidate,
  })
}
