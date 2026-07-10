import { ArrowLeftOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Button, Empty, Spin, Typography } from 'antd'
import dayjs from 'dayjs'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { GajiResponse } from '../api/types'

export default function GajiBreakdownPage() {
  const { bulan } = useParams<{ bulan: string }>()
  const navigate = useNavigate()

  const { isLoading } = useQuery({
    queryKey: ['gaji', bulan],
    queryFn: async () =>
      (await api.get<GajiResponse>('/portal/gaji/', { params: { bulan } })).data,
    enabled: Boolean(bulan),
  })

  const bulanLabel = bulan ? dayjs(bulan).format('MMMM YYYY') : ''

  return (
    <div>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        style={{ paddingLeft: 0, marginBottom: 8 }}
        onClick={() => navigate('/gaji')}
      >
        Kembali
      </Button>
      <Typography.Title level={3} style={{ marginTop: 0 }}>
        Rincian Gaji — {bulanLabel}
      </Typography.Title>

      {isLoading ? (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <Spin />
        </div>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Rincian komponen gaji akan ditampilkan di sini."
        />
      )}
    </div>
  )
}
