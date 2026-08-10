import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { Absensi } from './types'

export function useMyAbsensi(bulan: string | undefined) {
  return useQuery({
    queryKey: ['my-absensi', bulan],
    queryFn: async () =>
      (await api.get<Absensi[]>('/portal/absensi/', { params: { bulan } })).data,
    enabled: Boolean(bulan),
  })
}
