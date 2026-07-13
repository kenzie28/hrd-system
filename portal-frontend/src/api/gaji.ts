import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { GajiResponse } from './types'

export function useGaji(bulan: string | undefined) {
  return useQuery({
    queryKey: ['gaji', bulan],
    queryFn: async () =>
      (await api.get<GajiResponse>('/portal/gaji/', { params: { bulan } })).data,
    enabled: Boolean(bulan),
  })
}
