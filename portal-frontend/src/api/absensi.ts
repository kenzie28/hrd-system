import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { Absensi, Kehadiran } from './types'

export function useMyAbsensi(bulan: string | undefined) {
  return useQuery({
    queryKey: ['my-absensi', bulan],
    queryFn: async () =>
      (await api.get<Absensi[]>('/portal/absensi/', { params: { bulan } })).data,
    enabled: Boolean(bulan),
  })
}

export function useMyKehadiran(bulan: string | undefined) {
  return useQuery({
    queryKey: ['my-kehadiran', bulan],
    queryFn: async () =>
      (await api.get<Kehadiran[]>('/portal/kehadiran/', { params: { bulan } })).data,
    enabled: Boolean(bulan),
  })
}
