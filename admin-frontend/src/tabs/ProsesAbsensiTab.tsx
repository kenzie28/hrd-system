import { useState } from 'react'
import { App, Button, Space, Typography } from 'antd'
import { useProsesKehadiran } from '../api/hooks'
import type { ProsesKehadiranResult } from '../api/types'

export function ProsesAbsensiTab() {
  const { message } = App.useApp()
  const [result, setResult] = useState<ProsesKehadiranResult | null>(null)
  const proses = useProsesKehadiran()

  const onProses = async () => {
    try {
      const data = await proses.mutateAsync()
      setResult(data)
      message.success('Kehadiran diproses.')
    } catch {
      message.error('Gagal memproses kehadiran.')
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Memproses absensi sebelum hari ini menjadi kehadiran (hadir, cuti, dan alpa).
        Proses yang sama berjalan otomatis setiap hari pukul 00:00.
      </Typography.Paragraph>
      <Button type="primary" loading={proses.isPending} onClick={onProses}>
        Proses
      </Button>
      {result && (
        <Typography.Text>
          Hadir {result.hadir}, Cuti {result.cuti}, Alpa {result.alpa}.
        </Typography.Text>
      )}
    </Space>
  )
}