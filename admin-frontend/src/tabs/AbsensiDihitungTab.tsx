import { useState } from 'react'
import { App as AntApp, Alert, Input, Switch, Table, Typography } from 'antd'
import axios from 'axios'
import { useGajiKaryawan, useUpdateGajiKaryawan } from '../api/hooks'
import type { GajiKaryawan } from '../api/types'

type FlagField = 'absensi_dihitung' | 'lembur_dibayar'

function errorMessage(err: unknown, field: FlagField) {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail) return detail
  }
  return field === 'lembur_dibayar'
    ? 'Gagal menyimpan lembur dibayar.'
    : 'Gagal menyimpan absensi dihitung.'
}

export function AbsensiDihitungTab() {
  const { data, isLoading, isError } = useGajiKaryawan()
  const update = useUpdateGajiKaryawan()
  const { message } = AntApp.useApp()
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pending, setPending] = useState<{
    id: string
    field: FlagField
    value: boolean
  } | null>(null)

  if (isError) {
    return <Alert type="error" showIcon message="Gagal memuat daftar karyawan." />
  }

  const needle = query.trim().toLowerCase()
  const rows = (data ?? []).filter((row) => {
    if (!needle) return true
    return (
      row.karyawan_id.toLowerCase().includes(needle) ||
      row.nama.toLowerCase().includes(needle)
    )
  })

  const onToggle = async (karyawan_id: string, field: FlagField, value: boolean) => {
    setPending({ id: karyawan_id, field, value })
    try {
      await update.mutateAsync({ karyawan_id, [field]: value })
    } catch (err) {
      message.error(errorMessage(err, field))
    } finally {
      setPending(null)
    }
  }

  const flagColumn = (title: string, field: FlagField) => ({
    title,
    dataIndex: field,
    width: 180,
    render: (value: boolean, row: GajiKaryawan) => {
      const saving = pending?.id === row.karyawan_id && pending.field === field
      return (
        <Switch
          checked={saving && pending ? pending.value : value}
          checkedChildren="Ya"
          unCheckedChildren="Tidak"
          loading={saving}
          disabled={pending != null && !saving}
          onChange={(checked) => onToggle(row.karyawan_id, field, checked)}
        />
      )
    },
  })

  return (
    <div>
      <Typography.Paragraph type="secondary">
        Matikan Absensi dihitung untuk karyawan yang tidak dipotong alpa, berapa pun
        hari alpa mereka. Kehadiran tetap dicatat. Nyalakan Lembur dibayar untuk
        karyawan yang lemburnya dibayar.
      </Typography.Paragraph>
      <Input.Search
        allowClear
        placeholder="Cari ID atau nama"
        style={{ maxWidth: 320, marginBottom: 16 }}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setPage(1)
        }}
      />
      <Table<GajiKaryawan>
        rowKey="karyawan_id"
        size="small"
        loading={isLoading}
        dataSource={rows}
        pagination={{
          current: page,
          pageSize: 20,
          showSizeChanger: false,
          onChange: setPage,
        }}
        scroll={{ x: true }}
        columns={[
          { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 140 },
          { title: 'Nama', dataIndex: 'nama' },
          flagColumn('Absensi dihitung', 'absensi_dihitung'),
          flagColumn('Lembur dibayar', 'lembur_dibayar'),
        ]}
      />
    </div>
  )
}
