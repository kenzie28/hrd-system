import { useState } from 'react'
import { Button, DatePicker, Space, Typography } from 'antd'
import type { Dayjs } from 'dayjs'
import { useNavigate } from 'react-router-dom'

export default function GajiPage() {
  const navigate = useNavigate()
  const [bulan, setBulan] = useState<Dayjs | null>(null)

  return (
    <div>
      <Typography.Title level={3}>Gaji</Typography.Title>
      <Typography.Paragraph type="secondary">
        Pilih bulan untuk melihat rincian gaji Anda.
      </Typography.Paragraph>
      <Space>
        <DatePicker
          picker="month"
          value={bulan}
          onChange={setBulan}
          placeholder="Pilih bulan"
        />
        <Button
          type="primary"
          disabled={!bulan}
          onClick={() => {
            if (bulan) {
              navigate(`/gaji/${bulan.format('YYYY-MM')}`)
            }
          }}
        >
          Lihat Rincian
        </Button>
      </Space>
    </div>
  )
}
