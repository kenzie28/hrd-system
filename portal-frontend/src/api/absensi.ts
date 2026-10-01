import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { Kehadiran } from './types'

export function useMyKehadiran(bulan: string | undefined) {
  return useQuery({
    queryKey: ['my-kehadiran', bulan],
    queryFn: async () =>
      (await api.get<Kehadiran[]>('/portal/kehadiran/', { params: { bulan } })).data,
    enabled: Boolean(bulan),
  })
}
