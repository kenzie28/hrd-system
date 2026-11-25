import { useState } from 'react'
import { App as AntApp, Button, DatePicker, Popconfirm, Select, Space, Typography } from 'antd'
import axios from 'axios'
import type { Dayjs } from 'dayjs'
import { useCreateDinasRange, useKaryawan } from '../api/hooks'

function errorDetail(err: unknown, fallback: string) {
  if (!axios.isAxiosError(err)) return fallback
  const data = err.response?.data
  if (typeof data !== 'object' || data === null) return fallback
  if (typeof data.detail === 'string' && data.detail.trim()) return data.detail
  for (const value of Object.values(data)) {
    if (typeof value === 'string' && value.trim()) return value
  }
  return fallback
}

function resultMessage(created: number, skipped: number) {
  if (created === 0) {
    return 'Tidak ada dinas baru. Semua hari sudah punya dinas atau lembur yang approved.'
  }
  const made = `Dinas dibuat untuk ${created} hari.`
  if (skipped === 0) return made
  return `${made} ${skipped} hari dilewati karena sudah ada dinas atau lembur yang approved.`
}

export function DinasTab() {
  const { message } = AntApp.useApp()
  const { data: karyawanList, isLoading } = useKaryawan()
  const createDinas = useCreateDinasRange()
  const [karyawanId, setKaryawanId] = useState<string>()
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)

  const karyawan = karyawanList?.find((row) => row.karyawan_id === karyawanId)
  const canSubmit = karyawanId !== undefined && range !== null
  const dayCount = range ? range[1].diff(range[0], 'day') + 1 : 0

  const handleCreate = async () => {
    if (!karyawanId || !range) return
    try {
      const result = await createDinas.mutateAsync({
        karyawan_id: karyawanId,
        tanggal_mulai: range[0].format('YYYY-MM-DD'),
        tanggal_selesai: range[1].format('YYYY-MM-DD'),
      })
      if (result.created === 0) {
        message.warning(resultMessage(result.created, result.skipped))
      } else {
        message.success(resultMessage(result.created, result.skipped))
      }
      setRange(null)
    } catch (err) {
      message.error(errorDetail(err, 'Gagal membuat dinas.'))
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary">
        Pilih karyawan dan rentang tanggal. Setiap hari dalam rentang itu dicatat
        sebagai dinas. Hari yang sudah punya dinas, atau lembur yang approved,
        dilewati.
      </Typography.Paragraph>
      <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 480 }}>
        <Select
          showSearch
          allowClear
          placeholder="Pilih karyawan"
          loading={isLoading}
          value={karyawanId}
          onChange={(value) => setKaryawanId(value)}
          optionFilterProp="label"
          style={{ width: '100%' }}
          options={karyawanList?.map((row) => ({
            value: row.karyawan_id,
            label: `${row.nama} (${row.karyawan_id})`,
          }))}
        />
        <DatePicker.RangePicker
          value={range}
          format="YYYY-MM-DD"
          style={{ width: '100%' }}
          placeholder={['Tanggal mulai', 'Tanggal selesai']}
          onChange={(values) => {
            if (values?.[0] && values?.[1]) {
              setRange([values[0].startOf('day'), values[1].startOf('day')])
            } else {
              setRange(null)
            }
          }}
        />
        <Popconfirm
          title="Buat dinas?"
          description={
            karyawan && range
              ? `${karyawan.nama} (${karyawan.karyawan_id}), ${range[0].format('YYYY-MM-DD')} s.d. ${range[1].format('YYYY-MM-DD')} (${dayCount} hari).`
              : undefined
          }
          onConfirm={handleCreate}
          okText="Buat"
          cancelText="Batal"
          disabled={!canSubmit}
        >
          <Button type="primary" disabled={!canSubmit} loading={createDinas.isPending}>
            Buat Dinas
          </Button>
        </Popconfirm>
      </Space>
    </div>
  )
}
