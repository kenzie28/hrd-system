import { useState } from 'react'
import { App, Button, DatePicker, Popconfirm, Space, Typography } from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import { useHapusKehadiran, useProsesKehadiran } from '../api/hooks'
import type { HapusKehadiranResult, ProsesKehadiranResult } from '../api/types'

export function ProsesAbsensiTab() {
  const { message } = App.useApp()
  const [month, setMonth] = useState<Dayjs>(() => dayjs())
  const [result, setResult] = useState<ProsesKehadiranResult | null>(null)
  const [removed, setRemoved] = useState<HapusKehadiranResult | null>(null)
  const proses = useProsesKehadiran()
  const hapus = useHapusKehadiran()

  const onProses = async () => {
    try {
      const data = await proses.mutateAsync()
      setResult(data)
      setRemoved(null)
      message.success('Kehadiran diproses.')
    } catch {
      message.error('Gagal memproses kehadiran.')
    }
  }

  const onHapus = async () => {
    try {
      const data = await hapus.mutateAsync(month.format('YYYY-MM'))
      setRemoved(data)
      setResult(null)
      message.success(`Kehadiran ${data.bulan} dihapus.`)
    } catch {
      message.error('Gagal menghapus kehadiran.')
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Memproses absensi sebelum hari ini menjadi kehadiran (hadir, cuti, dan alpa).
        Proses yang sama berjalan otomatis setiap hari pukul 00:00.
      </Typography.Paragraph>
      <Space wrap>
        <Button type="primary" loading={proses.isPending} onClick={onProses}>
          Proses
        </Button>
        <DatePicker
          picker="month"
          value={month}
          onChange={(value) => value && setMonth(value)}
          allowClear={false}
        />
        <Popconfirm
          title={`Hapus kehadiran ${month.format('YYYY-MM')}?`}
          description="Absensi mentah tidak dihapus."
          okText="Hapus"
          cancelText="Batal"
          okButtonProps={{ danger: true }}
          onConfirm={onHapus}
        >
          <Button danger loading={hapus.isPending}>
            Hapus Kehadiran
          </Button>
        </Popconfirm>
      </Space>
      {result && (
        <Typography.Text>
          Hadir {result.hadir}, Cuti {result.cuti}, Alpa {result.alpa}.
        </Typography.Text>
      )}
      {removed && (
        <Typography.Text>
          Dihapus {removed.deleted} kehadiran untuk {removed.bulan}.
        </Typography.Text>
      )}
    </Space>
  )
}